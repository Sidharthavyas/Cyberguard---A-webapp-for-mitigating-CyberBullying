"""
Platform Manager - Dynamic polling management for multiple platforms.
Only runs pollers for connected platforms to minimize memory/CPU usage.
"""

import asyncio
import logging
from typing import Dict, Optional, Set
from datetime import datetime

logger = logging.getLogger(__name__)


class PlatformPoller:
    """Base class for platform pollers"""
    
    def __init__(self, platform_name: str):
        self.platform_name = platform_name
        self.is_running = False
        self.task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the poller"""
        if self.is_running:
            logger.warning(f"{self.platform_name} poller already running")
            return
        
        self.is_running = True
        self.task = asyncio.create_task(self._poll_loop())
        logger.info(f"✓ {self.platform_name} poller started")
    
    async def stop(self):
        """Stop the poller"""
        if not self.is_running:
            return
        
        self.is_running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        
        logger.info(f"✗ {self.platform_name} poller stopped")
    
    async def _poll_loop(self):
        """Override in subclass"""
        raise NotImplementedError


class PlatformManager:
    """
    Manages dynamic polling for multiple platforms.
    Only runs pollers for platforms that users have connected.
    """
    
    def __init__(self):
        self.active_pollers: Dict[str, PlatformPoller] = {}
        self.connected_platforms: Set[str] = set()
        logger.info("Platform Manager initialized")
    
    async def connect_platform(self, platform: str, credentials: dict, poller_class):
        """
        Connect a new platform and start its poller.
        
        Args:
            platform: Platform name (twitter, discord, reddit)
            credentials: Platform-specific credentials
            poller_class: Poller class for this platform
        """
        if platform in self.connected_platforms:
            logger.warning(f"{platform} already connected")
            return
        
        try:
            # Create and start poller
            poller = poller_class(credentials)
            await poller.start()
            
            # Track the poller
            self.active_pollers[platform] = poller
            self.connected_platforms.add(platform)
            
            logger.info(f"✓ {platform} connected successfully")
            
        except Exception as e:
            logger.error(f"Failed to connect {platform}: {e}")
            raise
    
    async def disconnect_platform(self, platform: str):
        """
        Disconnect a platform and stop its poller.
        
        Args:
            platform: Platform name to disconnect
        """
        if platform not in self.connected_platforms:
            logger.warning(f"{platform} not connected")
            return
        
        try:
            # Stop poller
            poller = self.active_pollers.get(platform)
            if poller:
                await poller.stop()
                del self.active_pollers[platform]
            
            # Remove from connected set
            self.connected_platforms.remove(platform)
            
            logger.info(f"✗ {platform} disconnected")
            
        except Exception as e:
            logger.error(f"Failed to disconnect {platform}: {e}")
            raise
    
    def get_connected_platforms(self) -> list:
        """Get list of currently connected platforms"""
        return list(self.connected_platforms)
    
    def is_platform_connected(self, platform: str) -> bool:
        """Check if a platform is connected"""
        return platform in self.connected_platforms
    
    async def shutdown(self):
        """Stop all pollers and cleanup"""
        logger.info("Shutting down all platform pollers...")
        
        for platform in list(self.connected_platforms):
            await self.disconnect_platform(platform)
        
        logger.info("All pollers stopped")


# Global singleton instance
platform_manager = PlatformManager()


def get_platform_manager() -> PlatformManager:
    """Get the global platform manager instance"""
    return platform_manager
