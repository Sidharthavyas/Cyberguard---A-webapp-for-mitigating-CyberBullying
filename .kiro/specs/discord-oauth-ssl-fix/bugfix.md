# Bugfix Requirements Document

## Introduction

The application is experiencing SSL handshake failures when exchanging OAuth authorization codes for access tokens with Discord's OAuth2 API. The error occurs in the `_do_discord_exchange` function in `backend/auth.py` when making HTTPS requests to `discord.com/api/oauth2/token`. The root cause is that the DNS-over-HTTPS (DoH) patch in `dns_resolver.py` resolves `discord.com` to IP addresses but returns those IPs in a way that breaks SSL/TLS Server Name Indication (SNI), causing the SSL handshake to fail with `SSLEOFError`.

The bug prevents users from completing the Discord OAuth login flow, as the token exchange step fails before the application can obtain an access token.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN the application attempts to exchange a Discord OAuth authorization code for an access token via POST to `https://discord.com/api/oauth2/token` THEN the system crashes with `SSLError: HTTPSConnectionPool(host='discord.com', port=443): Max retries exceeded with url: /api/oauth2/token (Caused by SSLError(SSLEOFError(8, '[SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of protocol (_ssl.c:1016)')))`

1.2 WHEN the application attempts to fetch user guilds via GET to `https://discord.com/api/users/@me/guilds` THEN the system experiences timeouts or SSL connection failures

1.3 WHEN the `_patched_getaddrinfo` function in `dns_resolver.py` resolves `discord.com` via DoH THEN the system returns address info tuples with IP addresses instead of the original hostname, breaking SSL/SNI verification

### Expected Behavior (Correct)

2.1 WHEN the application attempts to exchange a Discord OAuth authorization code for an access token via POST to `https://discord.com/api/oauth2/token` THEN the system SHALL successfully complete the SSL handshake and receive a valid token response without SSL errors

2.2 WHEN the application attempts to fetch user guilds via GET to `https://discord.com/api/users/@me/guilds` THEN the system SHALL successfully complete the SSL handshake and receive the guilds data without timeouts or SSL errors

2.3 WHEN the `_patched_getaddrinfo` function in `dns_resolver.py` resolves `discord.com` via DoH THEN the system SHALL preserve the original hostname in the connection context so that SSL/SNI verification can succeed while still using the DoH-resolved IP address for the actual connection

### Unchanged Behavior (Regression Prevention)

3.1 WHEN the application makes HTTPS requests to domains NOT in the `_DOH_HOSTS` set THEN the system SHALL CONTINUE TO use the original `socket.getaddrinfo` function without DoH resolution

3.2 WHEN the DoH DNS cache contains a valid entry for a hostname THEN the system SHALL CONTINUE TO return the cached IP addresses without making additional DoH requests

3.3 WHEN the application exchanges Twitter OAuth codes for tokens THEN the system SHALL CONTINUE TO function correctly without SSL errors

3.4 WHEN the application stores Discord tokens in Redis after successful authentication THEN the system SHALL CONTINUE TO store the tokens with the correct structure and expiration time

3.5 WHEN users authorize the Discord OAuth application and are redirected back with a valid authorization code and state parameter THEN the system SHALL CONTINUE TO validate the state parameter correctly
