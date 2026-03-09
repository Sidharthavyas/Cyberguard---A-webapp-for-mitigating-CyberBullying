"""
DNS-over-HTTPS resolver for HuggingFace Spaces.

HF Spaces blocks DNS resolution for certain domains (discord.com, etc.).
This module resolves hostnames via Cloudflare's DoH endpoint (https://1.1.1.1/dns-query)
and patches socket.getaddrinfo so all libraries (aiohttp, requests) work transparently.
"""

import logging
import socket
import time
import threading
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# DNS cache: hostname -> (ip_list, expiry_timestamp)
_dns_cache: Dict[str, Tuple[List[str], float]] = {}
DNS_CACHE_TTL = 300  # 5 minutes

# Hosts to intercept
_DOH_HOSTS = {"discord.com"}

# Thread lock for getaddrinfo patching safety
_patch_lock = threading.Lock()
_patched = False


def resolve_via_doh_sync(hostname: str) -> List[str]:
    """
    Resolve a hostname via Cloudflare DNS-over-HTTPS (synchronous).
    Uses 1.1.1.1 IP directly, so no DNS needed to reach Cloudflare.
    """
    # Check cache first
    if hostname in _dns_cache:
        ips, expiry = _dns_cache[hostname]
        if time.time() < expiry:
            return ips

    try:
        import requests as sync_requests

        resp = sync_requests.get(
            f"https://1.1.1.1/dns-query?name={hostname}&type=A",
            headers={"Accept": "application/dns-json"},
            timeout=10,
            verify=True,
        )
        resp.raise_for_status()
        data = resp.json()

        ips = [
            a["data"]
            for a in data.get("Answer", [])
            if a.get("type") == 1  # A records only
        ]

        if ips:
            _dns_cache[hostname] = (ips, time.time() + DNS_CACHE_TTL)
            logger.info(f"DoH resolved {hostname} -> {ips}")
            return ips
        else:
            logger.warning(f"DoH returned no A records for {hostname}")
            return []

    except Exception as e:
        logger.error(f"DoH resolution failed for {hostname}: {e}")
        return []


# ---- Global socket.getaddrinfo patch ----
# This is the most reliable way to bypass HF Spaces DNS restrictions.
# It intercepts DNS lookups for specific hosts and returns pre-resolved IPs.

_original_getaddrinfo = socket.getaddrinfo


def _patched_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    """
    Patched getaddrinfo that resolves blocked hosts via DoH.
    Falls back to original getaddrinfo for all other hosts.
    """
    if host in _DOH_HOSTS:
        ips = resolve_via_doh_sync(host)
        if ips:
            # Return the resolved IP but let the caller use the original hostname
            # for SSL/SNI purposes (handled by higher-level libraries)
            results = []
            for ip in ips:
                # Call original getaddrinfo with the IP (numeric, always resolves)
                try:
                    addr_info = _original_getaddrinfo(
                        ip, port, family, type, proto, flags | socket.AI_NUMERICHOST
                    )
                    results.extend(addr_info)
                except Exception:
                    # Construct manually if getaddrinfo with numeric fails
                    results.append(
                        (socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port or 443))
                    )
            if results:
                logger.debug(f"DNS override: {host} -> {ips[0]}")
                return results

    # Fall back to original DNS
    return _original_getaddrinfo(host, port, family, type, proto, flags)


def install_doh_patch():
    """
    Install the global socket.getaddrinfo patch.
    Call this once at application startup.
    Safe to call multiple times (idempotent).
    """
    global _patched
    with _patch_lock:
        if not _patched:
            socket.getaddrinfo = _patched_getaddrinfo
            _patched = True
            logger.info(
                f"Installed DoH DNS patch for: {', '.join(_DOH_HOSTS)}"
            )


def uninstall_doh_patch():
    """Restore original socket.getaddrinfo."""
    global _patched
    with _patch_lock:
        if _patched:
            socket.getaddrinfo = _original_getaddrinfo
            _patched = False
            logger.info("Removed DoH DNS patch")


def add_doh_host(hostname: str):
    """Add a hostname to the DoH interception list."""
    _DOH_HOSTS.add(hostname)
    logger.info(f"Added {hostname} to DoH hosts: {_DOH_HOSTS}")
