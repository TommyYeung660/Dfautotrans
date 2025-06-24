"""Page navigation controller for Dead Frontier Auto Trading System."""

import re
from typing import Optional, Dict, Any
from playwright.async_api import Page, Browser
from loguru import logger

from ..config.settings import Settings
from ..automation.browser_manager import BrowserManager


class NavigationError(Exception):
    """Navigation-related error."""
    pass


class PageNavigator:
    """Handles navigation between Dead Frontier pages."""
    
    def __init__(self, browser_manager: BrowserManager, settings: Settings):
        self.browser_manager = browser_manager
        self.settings = settings
        self.page: Optional[Page] = None
        self._current_url = ""
        self._cash_cache: Optional[int] = None
        self._login_status_cache: Optional[bool] = None
        
    async def initialize(self) -> bool:
        """Initialize page navigator."""
        try:
            await self.browser_manager.initialize()
            self.page = self.browser_manager.page
            if self.page is None:
                raise NavigationError("Failed to get page instance from browser manager")
            logger.info("Page navigator initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize page navigator: {e}")
            return False
    
    async def navigate_to_url(self, url: str, expected_indicators: Optional[list] = None) -> bool:
        """Navigate to a specific URL with validation."""
        if self.page is None:
            raise NavigationError("Page not initialized")
        
        try:
            logger.info(f"Navigating to: {url}")
            
            # Navigate to URL
            response = await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
            
            if response is None or not response.ok:
                logger.error(f"Failed to load page: {url} - Response status: {response.status if response else 'No response'}")
                return False
            
            # Wait for page to be ready
            await self.page.wait_for_load_state("networkidle", timeout=10000)
            
            # Update current URL
            self._current_url = self.page.url
            
            # Validate page loaded correctly
            if expected_indicators:
                for indicator in expected_indicators:
                    try:
                        await self.page.wait_for_selector(indicator, timeout=5000)
                    except Exception:
                        logger.warning(f"Expected indicator not found: {indicator}")
            
            logger.info(f"Navigation successful: {url}")
            
            # Clear cache after navigation
            self._cash_cache = None
            self._login_status_cache = None
            
            return True
            
        except Exception as e:
            logger.error(f"Navigation failed to {url}: {e}")
            return False
    
    async def navigate_to_login(self) -> bool:
        """Navigate to login page."""
        return await self.navigate_to_url(
            self.settings.login_url,
            expected_indicators=["#login_form", "input[name='username']", "input[name='password']"]
        )
    
    async def navigate_to_home(self) -> bool:
        """Navigate to home page."""
        return await self.navigate_to_url(
            self.settings.home_url,
            expected_indicators=["body", ".content"]
        )
    
    async def navigate_to_marketplace(self) -> bool:
        """Navigate to marketplace page."""
        return await self.navigate_to_url(
            self.settings.marketplace_url,
            expected_indicators=[".marketplace", ".inventory", ".market-item"]
        )
    
    async def navigate_to_bank(self) -> bool:
        """Navigate to bank page."""
        return await self.navigate_to_url(
            self.settings.bank_url,
            expected_indicators=[".bank", ".withdraw", ".balance"]
        )
    
    async def navigate_to_storage(self) -> bool:
        """Navigate to storage page."""
        return await self.navigate_to_url(
            self.settings.storage_url,
            expected_indicators=[".storage", ".inventory", ".deposit"]
        )
    
    async def check_login_status(self, force_refresh: bool = False) -> bool:
        """Check if user is currently logged in.
        
        Args:
            force_refresh: If True, bypass cache and perform fresh check
        """
        if self.page is None:
            return False
        
        # Use cache if available and not forcing refresh
        if not force_refresh and self._login_status_cache is not None:
            logger.debug(f"Using cached login status: {self._login_status_cache}")
            return self._login_status_cache
        
        try:
            # Check current URL
            current_url = self.page.url
            logger.debug(f"Checking login status for URL: {current_url}")
            
            # If we're on login page, we're definitely not logged in
            if "autologin=1" in current_url or "login" in current_url.lower():
                # Double check by looking for login form
                login_form = await self.page.query_selector("#login_form, .login-form, [name='username'], iframe[name*='fancybox-frame']")
                if login_form:
                    logger.debug("Found login form, user not logged in")
                    self._login_status_cache = False
                    return False
            
            # If we're on fairview subdomain, check for game content
            if "fairview.deadfrontier.com" in current_url:
                logger.debug("On fairview domain, checking for user-specific content")
                
                # Primary indicators (most reliable)
                primary_indicators = [
                    "a[href*='logout']",  # Logout link is strongest indicator
                    "text=/Cash: \\$[\\d,]+/",  # Cash display
                    "text=/Level \\d+/",  # Level display
                ]
                
                for selector in primary_indicators:
                    try:
                        element = await self.page.wait_for_selector(selector, timeout=2000)
                        if element:
                            logger.debug(f"Found primary login indicator: {selector}")
                            self._login_status_cache = True
                            return True
                    except:
                        continue
                
                # Secondary indicators (less reliable but still good)
                secondary_indicators = [
                    "generic:has-text('Health')",
                    "generic:has-text('Hunger')",
                    "generic:has-text('Thirst')",
                    ".character-info",
                    ".player-stats"
                ]
                
                for selector in secondary_indicators:
                    try:
                        element = await self.page.query_selector(selector)
                        if element:
                            logger.debug(f"Found secondary login indicator: {selector}")
                            self._login_status_cache = True
                            return True
                    except:
                        continue
                
                # Page content analysis (fallback)
                try:
                    page_content = await self.page.content()
                    login_indicators = ["cash:", "level:", "health:", "hunger:", "thirst:", "logout"]
                    
                    found_indicators = [indicator for indicator in login_indicators if indicator in page_content.lower()]
                    
                    if found_indicators:
                        logger.debug(f"Found login indicators in page content: {found_indicators}")
                        self._login_status_cache = True
                        return True
                    
                    # Check for login-related content that indicates NOT logged in
                    login_page_indicators = ["log in", "create account", "username", "password"]
                    found_login_page = [indicator for indicator in login_page_indicators if indicator in page_content.lower()]
                    
                    if found_login_page:
                        logger.debug(f"Found login page indicators: {found_login_page}")
                        self._login_status_cache = False
                        return False
                        
                except Exception as e:
                    logger.debug(f"Page content analysis failed: {e}")
                
                # If on fairview domain but no clear indicators, try a navigation test
                logger.debug("No clear indicators on fairview domain, performing navigation test...")
                try:
                    # Try to access a protected resource
                    response = await self.page.goto(
                        "https://fairview.deadfrontier.com/onlinezombiemmo/index.php?page=15",  # Bank page
                        wait_until="domcontentloaded",
                        timeout=5000
                    )
                    
                    if response and response.ok:
                        await asyncio.sleep(1)  # Brief wait for page to render
                        
                        # Check if we're still on fairview (not redirected to login)
                        final_url = self.page.url
                        if "fairview.deadfrontier.com" in final_url and "autologin" not in final_url:
                            logger.debug("Navigation test successful - user appears to be logged in")
                            self._login_status_cache = True
                            return True
                        
                except Exception as e:
                    logger.debug(f"Navigation test failed: {e}")
                
                # If we reach here on fairview domain, assume not logged in
                logger.debug("On fairview domain but no login indicators found")
                self._login_status_cache = False
                return False
            
            # Try to find logout link or user info on other pages
            logout_link = await self.page.query_selector("a[href*='logout'], .logout")
            user_info = await self.page.query_selector(".user-info, .character-info, .player-name")
            
            if logout_link or user_info:
                logger.debug("Found logout link or user info on non-fairview page")
                self._login_status_cache = True
                return True
            
            logger.debug("No login indicators found, assuming not logged in")
            self._login_status_cache = False
            return False
            
        except Exception as e:
            logger.error(f"Error checking login status: {e}")
            self._login_status_cache = False
            return False
    
    async def ensure_logged_in(self) -> bool:
        """Ensure user is logged in, navigate to login if needed."""
        if await self.check_login_status():
            logger.info("User is already logged in")
            return True
        
        logger.info("User not logged in, navigating to login page")
        return await self.navigate_to_login()
    
    async def get_current_cash(self) -> Optional[int]:
        """Extract current cash amount from page."""
        if self.page is None:
            return None
        
        # Use cache if available and fresh
        if self._cash_cache is not None:
            return self._cash_cache
        
        try:
            # Common selectors for cash display
            cash_selectors = [
                ".cash", ".money", ".funds", ".balance",
                "#cash", "#money", "#funds", "#balance",
                "[data-cash]", "[data-money]"
            ]
            
            for selector in cash_selectors:
                element = await self.page.query_selector(selector)
                if element:
                    text = await element.inner_text()
                    cash = self._extract_number_from_text(text)
                    if cash is not None:
                        self._cash_cache = cash
                        logger.debug(f"Found cash amount: ${cash}")
                        return cash
            
            # Try to find cash in page scripts
            scripts = await self.page.query_selector_all("script")
            for script in scripts:
                content = await script.inner_text()
                
                # Look for cash patterns in JavaScript
                cash_patterns = [
                    r'cash["\']?\s*[:=]\s*(\d+)',
                    r'money["\']?\s*[:=]\s*(\d+)',
                    r'funds["\']?\s*[:=]\s*(\d+)',
                    r'\$(\d+)',
                    r'Cash:\s*\$?(\d+)'
                ]
                
                for pattern in cash_patterns:
                    match = re.search(pattern, content, re.IGNORECASE)
                    if match:
                        cash = int(match.group(1))
                        self._cash_cache = cash
                        logger.debug(f"Found cash in script: ${cash}")
                        return cash
            
            # Try to find cash in page text
            page_text = await self.page.inner_text("body")
            cash_match = re.search(r'Cash:\s*\$?(\d+)|Money:\s*\$?(\d+)|\$(\d+)', page_text, re.IGNORECASE)
            if cash_match:
                cash = int(next(group for group in cash_match.groups() if group is not None))
                self._cash_cache = cash
                logger.debug(f"Found cash in page text: ${cash}")
                return cash
            
            logger.warning("Could not find cash amount on page")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting cash amount: {e}")
            return None
    
    def _extract_number_from_text(self, text: str) -> Optional[int]:
        """Extract numeric value from text string."""
        if not text:
            return None
        
        # Remove common currency symbols and formatting
        cleaned = re.sub(r'[$,\s]', '', text)
        
        # Extract number
        match = re.search(r'(\d+)', cleaned)
        if match:
            return int(match.group(1))
        
        return None
    
    async def wait_for_page_load(self, timeout: int = 30000) -> bool:
        """Wait for page to fully load."""
        if self.page is None:
            return False
        
        try:
            await self.page.wait_for_load_state("networkidle", timeout=timeout)
            return True
        except Exception as e:
            logger.error(f"Page load timeout: {e}")
            return False
    
    async def refresh_page(self) -> bool:
        """Refresh current page."""
        if self.page is None:
            return False
        
        try:
            await self.page.reload(wait_until="networkidle", timeout=30000)
            # Clear cache after refresh
            self._cash_cache = None
            self._login_status_cache = None
            return True
        except Exception as e:
            logger.error(f"Page refresh failed: {e}")
            return False
    
    def get_current_url(self) -> str:
        """Get current page URL."""
        if self.page is None:
            return ""
        return self.page.url
    
    def clear_cache(self) -> None:
        """Clear cached values."""
        self._cash_cache = None
        self._login_status_cache = None
        logger.debug("Page navigator cache cleared")
    
    async def is_page_responsive(self) -> bool:
        """Check if page is responsive."""
        if self.page is None:
            return False
        
        try:
            # Try to evaluate simple JavaScript
            result = await self.page.evaluate("() => document.readyState")
            return result == "complete"
        except Exception:
            return False
    
    async def get_page_title(self) -> str:
        """Get current page title."""
        if self.page is None:
            return ""
        
        try:
            return await self.page.title()
        except Exception:
            return ""
    
    async def close(self) -> None:
        """Clean up page navigator."""
        logger.info("Closing page navigator")
        # Browser manager handles browser cleanup 