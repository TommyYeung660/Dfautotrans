"""Anti-detection and human behavior simulation for Dead Frontier Auto Trading System."""

import asyncio
import random
import time
from typing import Tuple, Optional, List
from playwright.async_api import Page, Locator

from ..config.settings import AntiDetectionConfig
from ..utils.logger import get_browser_logger

logger = get_browser_logger()


class HumanBehaviorSimulator:
    """Simulates human-like behavior to avoid detection."""
    
    def __init__(self, config: AntiDetectionConfig):
        self.config = config
        
    async def random_delay(self, min_delay: Optional[int] = None, max_delay: Optional[int] = None) -> None:
        """Add random delay to simulate human thinking time.
        
        Args:
            min_delay: Minimum delay in milliseconds. Uses config default if None.
            max_delay: Maximum delay in milliseconds. Uses config default if None.
        """
        min_ms = min_delay or self.config.action_delay_min
        max_ms = max_delay or self.config.action_delay_max
        
        delay_ms = random.randint(min_ms, max_ms)
        logger.debug(f"Random delay: {delay_ms}ms")
        await asyncio.sleep(delay_ms / 1000)
    
    async def random_pause(self) -> None:
        """Randomly pause to simulate human distraction."""
        if random.random() < self.config.random_pause_probability:
            pause_duration = random.randint(1000, 5000)  # 1-5 seconds
            logger.debug(f"Random pause: {pause_duration}ms")
            await asyncio.sleep(pause_duration / 1000)
    
    async def human_like_mouse_movement(self, page: Page, target_selector: str) -> None:
        """Move mouse in human-like pattern to target element.
        
        Args:
            page: Playwright page instance
            target_selector: CSS selector of target element
        """
        try:
            # Get current viewport size
            viewport = page.viewport_size
            if not viewport:
                viewport = {"width": 1920, "height": 1080}
            
            # Get target element position
            element = page.locator(target_selector)
            if await element.count() == 0:
                logger.warning(f"Target element not found: {target_selector}")
                return
            
            box = await element.bounding_box()
            if not box:
                logger.warning(f"Could not get bounding box for: {target_selector}")
                return
            
            # Calculate target position with some randomness
            target_x = box["x"] + box["width"] / 2 + random.randint(-10, 10)
            target_y = box["y"] + box["height"] / 2 + random.randint(-5, 5)
            
            # Move mouse in curved path
            await self._move_mouse_curved(page, target_x, target_y)
            
        except Exception as e:
            logger.error(f"Error in human-like mouse movement: {e}")
    
    async def _move_mouse_curved(self, page: Page, target_x: float, target_y: float) -> None:
        """Move mouse in a curved, human-like path.
        
        Args:
            page: Playwright page instance
            target_x: Target X coordinate
            target_y: Target Y coordinate
        """
        # Get current mouse position (approximate)
        current_x = random.randint(100, 800)
        current_y = random.randint(100, 600)
        
        # Calculate intermediate points for curved movement
        steps = random.randint(3, 7)
        points = []
        
        for i in range(steps + 1):
            progress = i / steps
            
            # Add some curve to the movement
            curve_offset_x = random.randint(-20, 20) * (0.5 - abs(progress - 0.5))
            curve_offset_y = random.randint(-15, 15) * (0.5 - abs(progress - 0.5))
            
            x = current_x + (target_x - current_x) * progress + curve_offset_x
            y = current_y + (target_y - current_y) * progress + curve_offset_y
            
            points.append((x, y))
        
        # Move through each point with slight delays
        for x, y in points:
            await page.mouse.move(x, y)
            await asyncio.sleep(random.randint(10, 50) / 1000)
    
    async def human_like_typing(self, element: Locator, text: str, clear_first: bool = True) -> None:
        """Type text in human-like manner with realistic delays.
        
        Args:
            element: Playwright locator for input element
            text: Text to type
            clear_first: Whether to clear the field first
        """
        try:
            if clear_first:
                await element.clear()
                await self.random_delay(100, 300)
            
            # Type each character with random delays
            for char in text:
                await element.type(char)
                
                # Random typing delay
                delay = random.randint(
                    self.config.typing_delay_min,
                    self.config.typing_delay_max
                )
                await asyncio.sleep(delay / 1000)
                
                # Occasional longer pause (thinking)
                if random.random() < 0.1:  # 10% chance
                    await asyncio.sleep(random.randint(200, 800) / 1000)
            
            logger.debug(f"Typed text: '{text}' with human-like delays")
            
        except Exception as e:
            logger.error(f"Error in human-like typing: {e}")
            raise
    
    async def human_like_click(self, element: Locator, page: Page) -> None:
        """Perform human-like click with movement and delays.
        
        Args:
            element: Playwright locator for element to click
            page: Playwright page instance
        """
        try:
            # Wait for element to be visible and enabled
            await element.wait_for(state="visible", timeout=5000)
            
            # Get element selector for mouse movement
            # This is a simplified approach - in practice you'd need the actual selector
            box = await element.bounding_box()
            if box:
                # Move mouse to element area first
                target_x = box["x"] + box["width"] / 2 + random.randint(-5, 5)
                target_y = box["y"] + box["height"] / 2 + random.randint(-3, 3)
                await page.mouse.move(target_x, target_y)
                
                # Brief pause before clicking
                await self.random_delay(100, 300)
            
            # Perform the click
            await element.click()
            logger.debug("Performed human-like click")
            
            # Brief pause after clicking
            await self.random_delay(200, 500)
            
        except Exception as e:
            logger.error(f"Error in human-like click: {e}")
            raise
    
    async def simulate_reading_delay(self, content_length: int = 100) -> None:
        """Simulate time spent reading content.
        
        Args:
            content_length: Approximate length of content to read
        """
        # Estimate reading time (average 200 words per minute, 5 chars per word)
        estimated_reading_time = (content_length / 5) / 200 * 60  # seconds
        
        # Add randomness and minimum/maximum bounds
        reading_time = max(0.5, min(10.0, estimated_reading_time * random.uniform(0.7, 1.3)))
        
        logger.debug(f"Simulating reading delay: {reading_time:.1f}s")
        await asyncio.sleep(reading_time)
    
    async def simulate_decision_making(self) -> None:
        """Simulate time spent making decisions."""
        decision_time = random.uniform(1.0, 4.0)  # 1-4 seconds
        logger.debug(f"Simulating decision making: {decision_time:.1f}s")
        await asyncio.sleep(decision_time)


class BrowserFingerprinting:
    """Handle browser fingerprinting countermeasures."""
    
    @staticmethod
    async def setup_stealth_mode(page: Page) -> None:
        """Setup stealth mode to avoid detection.
        
        Args:
            page: Playwright page instance
        """
        # Override navigator properties
        await page.add_init_script("""
            // Override navigator.webdriver
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            
            // Override navigator.plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            
            // Override navigator.languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
            });
            
            // Override screen properties with realistic values
            Object.defineProperty(screen, 'availHeight', {
                get: () => 1040,
            });
            Object.defineProperty(screen, 'availWidth', {
                get: () => 1920,
            });
        """)
        
        # Set realistic user agent
        await page.set_extra_http_headers({
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        })
        
        logger.debug("Stealth mode configured")
    
    @staticmethod
    async def randomize_viewport(page: Page) -> None:
        """Randomize viewport size within realistic bounds.
        
        Args:
            page: Playwright page instance
        """
        # Common desktop resolutions with slight randomization
        base_resolutions = [
            (1920, 1080),
            (1366, 768),
            (1536, 864),
            (1440, 900),
            (1280, 720)
        ]
        
        base_width, base_height = random.choice(base_resolutions)
        
        # Add small random variations
        width = base_width + random.randint(-50, 50)
        height = base_height + random.randint(-30, 30)
        
        await page.set_viewport_size({"width": width, "height": height})
        logger.debug(f"Viewport set to {width}x{height}")


class AntiDetectionManager:
    """Main anti-detection manager."""
    
    def __init__(self, config: AntiDetectionConfig):
        self.config = config
        self.behavior_simulator = HumanBehaviorSimulator(config)
        self.fingerprinting = BrowserFingerprinting()
    
    async def setup_page(self, page: Page) -> None:
        """Setup page with anti-detection measures.
        
        Args:
            page: Playwright page instance
        """
        await self.fingerprinting.setup_stealth_mode(page)
        await self.fingerprinting.randomize_viewport(page)
        logger.info("Anti-detection setup completed")
    
    async def safe_navigate(self, page: Page, url: str) -> None:
        """Navigate to URL with human-like behavior.
        
        Args:
            page: Playwright page instance
            url: URL to navigate to
        """
        logger.info(f"Navigating to: {url}")
        
        # Random delay before navigation
        await self.behavior_simulator.random_delay(500, 2000)
        
        # Navigate
        await page.goto(url, wait_until="domcontentloaded")
        
        # Simulate page loading and reading time
        await self.behavior_simulator.simulate_reading_delay(200)
        await self.behavior_simulator.random_pause()
        
        logger.info("Navigation completed")
    
    async def safe_click(self, element: Locator, page: Page) -> None:
        """Perform safe click with anti-detection measures.
        
        Args:
            element: Element to click
            page: Page instance
        """
        await self.behavior_simulator.random_pause()
        await self.behavior_simulator.human_like_click(element, page)
    
    async def safe_type(self, element: Locator, text: str) -> None:
        """Perform safe typing with anti-detection measures.
        
        Args:
            element: Element to type in
            text: Text to type
        """
        await self.behavior_simulator.random_delay(200, 800)
        await self.behavior_simulator.human_like_typing(element, text)
    
    async def simulate_user_behavior(self) -> None:
        """Simulate general user behavior patterns."""
        await self.behavior_simulator.random_pause()
        await self.behavior_simulator.simulate_decision_making() 