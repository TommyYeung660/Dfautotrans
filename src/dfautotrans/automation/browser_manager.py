"""Browser management for Dead Frontier Auto Trading System."""

import asyncio
from typing import Optional, List, Dict, Any
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Locator

from ..config.settings import Settings, BrowserConfig
from ..data.models import MarketItemData, UserProfileData, SearchResult
from ..utils.logger import get_browser_logger
from .anti_detection import AntiDetectionManager

logger = get_browser_logger()


class DeadFrontierSelectors:
    """CSS selectors for Dead Frontier elements based on MCP testing."""
    
    # Marketplace selectors
    SEARCH_INPUT = 'input[type="text"]'  # Search input field
    SEARCH_BUTTON = 'button:has-text("search")'  # Search button
    CATEGORY_DROPDOWN = 'select'  # Category dropdown
    
    # Navigation tabs
    TAB_BUYING = 'button:has-text("buying")'
    TAB_SELLING = 'button:has-text("selling")'
    TAB_PRIVATE = 'button:has-text("private")'
    TAB_ITEM_FOR_ITEM = 'button:has-text("item-for-item")'
    
    # Market items (based on MCP test structure)
    MARKET_ITEMS = 'table tr'  # Market item rows
    BUY_BUTTON = 'button[data-action="buyItem"]'  # Buy buttons
    SELLER_LINK = 'a[href*="action=profile"]'  # Seller profile links
    
    # User info selectors
    USER_CASH = 'text=/Cash: \\$[\\d,]+/'
    USER_LEVEL = 'text=/Level \\d+/'
    USER_NAME = 'text=/\\w+/'  # Username pattern
    
    # Inventory selectors
    INVENTORY_ITEMS = 'table td'  # Inventory slots
    
    # Error/status selectors
    DISABLED_BUTTON = 'button[disabled]'
    
    @staticmethod
    def buy_button_for_item(item_location: str, buy_num: str) -> str:
        """Get specific buy button selector for an item."""
        return f'button[data-item-location="{item_location}"][data-buynum="{buy_num}"]'


class BrowserManager:
    """Manages browser automation for Dead Frontier."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.browser_config = settings.browser
        self.anti_detection = AntiDetectionManager(settings.anti_detection)
        
        # Browser instances
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        
        # State tracking
        self.is_logged_in = False
        self.current_page_type = None
        self._initialized = False
        self._error_count = 0
        self._max_errors = 5
        self._last_page_load_time = None
        
        # Enhanced monitoring
        self._page_load_timeout = settings.browser.timeout
        self._network_errors = []
        self._performance_metrics = {}
        
    async def start(self) -> None:
        """Start browser and initialize context."""
        try:
            logger.info("Starting browser...")
            
            self.playwright = await async_playwright().start()
            
            # Launch browser
            self.browser = await self.playwright.chromium.launch(
                headless=self.browser_config.headless,
                slow_mo=self.browser_config.slow_mo,
                args=[
                    '--no-sandbox',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor'
                ]
            )
            
            # Create context
            self.context = await self.browser.new_context(
                viewport={
                    'width': self.browser_config.viewport_width,
                    'height': self.browser_config.viewport_height
                },
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            # Create page
            self.page = await self.context.new_page()
            
            # Setup anti-detection
            await self.anti_detection.setup_page(self.page)
            
            # Set default timeout
            self.page.set_default_timeout(self.browser_config.timeout)
            
            # Set up performance monitoring
            await self._setup_performance_monitoring()
            
            self._initialized = True
            logger.info("Browser started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start browser: {e}")
            await self.cleanup()
            raise
    
    async def cleanup(self) -> None:
        """Clean up browser resources."""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            
            logger.info("Browser cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during browser cleanup: {e}")
    
    async def ensure_logged_in(self, login_handler=None) -> bool:
        """Ensure user is logged in using the dedicated LoginHandler.
        
        Args:
            login_handler: LoginHandler instance to use for login
            
        Returns:
            True if login successful, False otherwise
        """
        if not self.page:
            raise RuntimeError("Browser not started")
        
        # If already logged in, return True
        if self.is_logged_in:
            return True
        
        # If no login handler provided, we can't login
        if not login_handler:
            logger.warning("No login handler provided and not logged in")
            return False
        
        try:
            # Use the dedicated login handler
            login_success = await login_handler.perform_login()
            if login_success:
                self.is_logged_in = True
                logger.info("Login successful via LoginHandler")
                return True
            else:
                logger.error("Login failed via LoginHandler")
                return False
                
        except Exception as e:
            logger.error(f"Error during login process: {e}")
            return False
    
    async def navigate_to_marketplace(self, login_handler=None) -> None:
        """Navigate to Dead Frontier marketplace.
        
        Args:
            login_handler: LoginHandler instance for authentication if needed
        """
        if not self.page:
            raise RuntimeError("Browser not started")
        
        # Ensure we're logged in first
        if not self.is_logged_in:
            logger.info("Not logged in, attempting login first...")
            login_success = await self.ensure_logged_in(login_handler)
            if not login_success:
                raise RuntimeError("Failed to login to Dead Frontier - please provide a LoginHandler instance")
        
        logger.info("Navigating to marketplace...")
        
        await self.anti_detection.safe_navigate(self.page, self.settings.marketplace_url)
        self.current_page_type = "marketplace"
        
        # Wait for page to load
        await self.page.wait_for_load_state("domcontentloaded")
        
        # Check what page we actually landed on
        page_title = await self.page.title()
        logger.info(f"Page title: {page_title}")
        
        # Verify we're on the marketplace
        if await self.page.locator(DeadFrontierSelectors.SEARCH_INPUT).count() > 0:
            logger.info("Successfully navigated to marketplace")
        else:
            logger.warning("Marketplace elements not found")
            # Take screenshot for debugging
            await self.take_screenshot("marketplace_navigation_debug.png")
            
            # Check if we need to login again
            if await self.page.locator('input[type="password"]').count() > 0:
                logger.warning("Login form detected - session may have expired")
                self.is_logged_in = False
    
    async def search_items(self, search_term: str, category: str = "Everything") -> SearchResult:
        """Search for items in the marketplace.
        
        Args:
            search_term: Item name to search for
            category: Category to search in
            
        Returns:
            SearchResult with found items
        """
        if not self.page:
            raise RuntimeError("Browser not started")
        
        logger.info(f"Searching for: '{search_term}' in category: '{category}'")
        
        try:
            # Ensure we're on buying tab
            await self._ensure_buying_tab()
            
            # Clear and type search term
            search_input = self.page.locator(DeadFrontierSelectors.SEARCH_INPUT)
            await self.anti_detection.safe_type(search_input, search_term)
            
            # Click search button
            search_button = self.page.locator(DeadFrontierSelectors.SEARCH_BUTTON)
            await self.anti_detection.safe_click(search_button, self.page)
            
            # Wait for results to load
            await self.page.wait_for_timeout(2000)
            
            # Parse search results
            items = await self._parse_market_items()
            
            result = SearchResult(
                items=items,
                total_found=len(items),
                search_term=search_term
            )
            
            logger.info(f"Found {len(items)} items for '{search_term}'")
            return result
            
        except Exception as e:
            logger.error(f"Error searching for items: {e}")
            raise
    
    async def _ensure_buying_tab(self) -> None:
        """Ensure we're on the buying tab."""
        try:
            # First check if we can find any marketplace elements
            buying_tab = self.page.locator(DeadFrontierSelectors.TAB_BUYING)
            
            # Wait for the element to exist with a shorter timeout
            await buying_tab.wait_for(state="visible", timeout=5000)
            
            # Check if buying tab is disabled (already selected)
            disabled_attr = await buying_tab.get_attribute("disabled")
            if disabled_attr is None:
                # Tab is not disabled, so we need to click it
                await self.anti_detection.safe_click(buying_tab, self.page)
                await self.page.wait_for_timeout(1000)
                
        except Exception as e:
            logger.warning(f"Could not ensure buying tab - may not be logged in: {e}")
            # Continue anyway - might be on a different page structure
    
    async def _parse_market_items(self) -> List[MarketItemData]:
        """Parse market items from current page.
        
        Returns:
            List of MarketItemData objects
        """
        items = []
        
        try:
            # Wait for market items to be visible
            await self.page.wait_for_selector("table", timeout=5000)
            
            # Get all table rows that might contain items
            rows = self.page.locator("table tr")
            row_count = await rows.count()
            
            for i in range(row_count):
                row = rows.nth(i)
                
                # Try to extract item data from row
                item_data = await self._extract_item_from_row(row)
                if item_data:
                    items.append(item_data)
            
        except Exception as e:
            logger.error(f"Error parsing market items: {e}")
        
        return items
    
    async def _extract_item_from_row(self, row: Locator) -> Optional[MarketItemData]:
        """Extract item data from a table row.
        
        Args:
            row: Playwright locator for table row
            
        Returns:
            MarketItemData if valid item found, None otherwise
        """
        try:
            # Look for buy button in this row
            buy_button = row.locator(DeadFrontierSelectors.BUY_BUTTON)
            if await buy_button.count() == 0:
                return None
            
            # Extract data attributes from buy button
            item_location = await buy_button.get_attribute("data-item-location")
            buy_num = await buy_button.get_attribute("data-buynum")
            
            if not item_location or not buy_num:
                return None
            
            # Extract other item information from row cells
            cells = row.locator("td")
            cell_count = await cells.count()
            
            if cell_count < 4:  # Need at least item name, zone, seller, price
                return None
            
            # Extract text from cells (this is a simplified approach)
            # In practice, you'd need to identify the exact cell positions
            item_name = await cells.nth(0).text_content() or "Unknown Item"
            trade_zone = await cells.nth(1).text_content() or ""
            seller = await cells.nth(2).text_content() or "Unknown Seller"
            price_text = await cells.nth(3).text_content() or "0"
            
            # Parse price (remove $ and commas)
            try:
                price = float(price_text.replace("$", "").replace(",", ""))
            except (ValueError, AttributeError):
                price = 0.0
            
            # Extract quantity (usually in parentheses in item name)
            quantity = 1
            if "(" in item_name and ")" in item_name:
                try:
                    qty_text = item_name[item_name.find("(")+1:item_name.find(")")]
                    quantity = int(qty_text)
                    item_name = item_name[:item_name.find("(")].strip()
                except (ValueError, IndexError):
                    pass
            
            return MarketItemData(
                item_name=item_name.strip(),
                seller=seller.strip(),
                trade_zone=trade_zone.strip() if trade_zone else None,
                price=price,
                quantity=quantity,
                buy_item_location=item_location,
                buy_num=buy_num
            )
            
        except Exception as e:
            logger.debug(f"Could not extract item from row: {e}")
            return None
    
    async def attempt_purchase(self, item: MarketItemData) -> bool:
        """Attempt to purchase an item.
        
        Args:
            item: MarketItemData with purchase information
            
        Returns:
            True if purchase successful, False otherwise
        """
        if not self.page or not item.buy_item_location or not item.buy_num:
            return False
        
        logger.info(f"Attempting to purchase: {item.item_name} from {item.seller} for ${item.price}")
        
        try:
            # Find the specific buy button for this item
            buy_button_selector = DeadFrontierSelectors.buy_button_for_item(
                item.buy_item_location, 
                item.buy_num
            )
            buy_button = self.page.locator(buy_button_selector)
            
            # Check if button exists and is enabled
            if await buy_button.count() == 0:
                logger.warning(f"Buy button not found for item: {item.item_name}")
                return False
            
            if await buy_button.get_attribute("disabled") is not None:
                logger.warning(f"Buy button disabled for item: {item.item_name} (insufficient funds?)")
                return False
            
            # Simulate decision making
            await self.anti_detection.simulate_user_behavior()
            
            # Click buy button
            await self.anti_detection.safe_click(buy_button, self.page)
            
            # Wait for potential confirmation dialog or page update
            await self.page.wait_for_timeout(2000)
            
            # Check for success indicators (this would need to be customized based on actual UI)
            # For now, we assume success if no error dialog appears
            
            logger.info(f"Purchase attempt completed for: {item.item_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error attempting purchase: {e}")
            return False
    
    async def get_user_profile(self) -> Optional[UserProfileData]:
        """Get current user profile information.
        
        Returns:
            UserProfileData if successful, None otherwise
        """
        if not self.page:
            return None
        
        try:
            # Extract user information from page
            # This is based on the user info structure we saw in MCP tests
            
            # Get username (this would need to be adjusted based on actual page structure)
            username_element = self.page.locator("text=/TOengin/")  # Example from MCP tests
            username = await username_element.text_content() if await username_element.count() > 0 else "Unknown"
            
            # Get cash amount
            cash_element = self.page.locator(DeadFrontierSelectors.USER_CASH)
            cash_text = await cash_element.text_content() if await cash_element.count() > 0 else "$0"
            cash = int(cash_text.replace("Cash: $", "").replace(",", "")) if cash_text else 0
            
            # Get level
            level_element = self.page.locator(DeadFrontierSelectors.USER_LEVEL)
            level_text = await level_element.text_content() if await level_element.count() > 0 else "Level 0"
            level = int(level_text.replace("Level ", "")) if level_text else 0
            
            return UserProfileData(
                username=username,
                cash=cash,
                level=level
            )
            
        except Exception as e:
            logger.error(f"Error getting user profile: {e}")
            return None
    
    async def switch_to_selling_tab(self) -> None:
        """Switch to selling tab in marketplace."""
        if not self.page:
            raise RuntimeError("Browser not started")
        
        selling_tab = self.page.locator(DeadFrontierSelectors.TAB_SELLING)
        await self.anti_detection.safe_click(selling_tab, self.page)
        await self.page.wait_for_timeout(1000)
        
        logger.info("Switched to selling tab")
    
    async def get_current_listings(self) -> List[MarketItemData]:
        """Get current user's selling listings.
        
        Returns:
            List of items currently being sold
        """
        # Switch to selling tab first
        await self.switch_to_selling_tab()
        
        # Parse selling items (implementation would be similar to _parse_market_items)
        # but focused on user's own listings
        return []
    
    async def cancel_sale(self, item_identifier: str) -> bool:
        """Cancel a sale listing.
        
        Args:
            item_identifier: Identifier for the item to cancel
            
        Returns:
            True if cancellation successful
        """
        try:
            # Look for cancel sale button
            cancel_button = self.page.locator('button:has-text("cancel sale")')
            if await cancel_button.count() > 0:
                await self.anti_detection.safe_click(cancel_button, self.page)
                await self.page.wait_for_timeout(1000)
                logger.info(f"Cancelled sale for: {item_identifier}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error cancelling sale: {e}")
            return False
    
    async def take_screenshot(self, filename: str = "screenshot.png") -> str:
        """Take a screenshot of current page.
        
        Args:
            filename: Screenshot filename
            
        Returns:
            Path to screenshot file
        """
        if not self.page:
            raise RuntimeError("Browser not started")
        
        screenshot_path = self.settings.logs_dir / filename
        await self.page.screenshot(path=str(screenshot_path))
        
        logger.info(f"Screenshot saved: {screenshot_path}")
        return str(screenshot_path)
    
    async def _setup_performance_monitoring(self) -> None:
        """Set up performance and error monitoring."""
        if not self.page:
            return
        
        # Monitor console errors
        self.page.on("console", self._handle_console_message)
        
        # Monitor network failures
        self.page.on("requestfailed", self._handle_network_error)
        
        # Monitor page crashes
        self.page.on("crash", self._handle_page_crash)
        
        logger.debug("Performance monitoring set up")
    
    def _handle_console_message(self, msg) -> None:
        """Handle console messages from the page."""
        if msg.type == "error":
            logger.warning(f"Console error: {msg.text}")
            self._error_count += 1
    
    def _handle_network_error(self, request) -> None:
        """Handle network request failures."""
        error_info = {
            'url': request.url,
            'method': request.method,
            'failure': request.failure,
            'timestamp': asyncio.get_event_loop().time()
        }
        self._network_errors.append(error_info)
        logger.warning(f"Network request failed: {request.url} - {request.failure}")
    
    def _handle_page_crash(self) -> None:
        """Handle page crashes."""
        logger.critical("Page crashed!")
        self._error_count = self._max_errors  # Force reinitialization
    
    async def is_browser_healthy(self) -> bool:
        """Check if browser is in a healthy state."""
        if not self._initialized or not self.page:
            return False
        
        try:
            # Check if page is responsive
            await self.page.evaluate("() => document.readyState", timeout=5000)
            
            # Check error count
            if self._error_count >= self._max_errors:
                logger.warning(f"Too many errors detected: {self._error_count}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Browser health check failed: {e}")
            return False
    
    async def recover_from_error(self) -> bool:
        """Attempt to recover from browser errors."""
        logger.info("Attempting browser recovery...")
        
        try:
            # Reset error count
            self._error_count = 0
            
            # Try to refresh the page
            if self.page:
                await self.page.reload(wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(2)
                
                # Verify recovery
                if await self.is_browser_healthy():
                    logger.info("Browser recovery successful")
                    return True
            
            # If reload failed, try full browser restart
            logger.info("Attempting full browser restart...")
            await self.cleanup()
            await asyncio.sleep(3)
            await self.start()
            
            if await self.is_browser_healthy():
                logger.info("Full browser restart successful")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Browser recovery failed: {e}")
            return False
    
    async def initialize(self) -> bool:
        """Initialize browser manager - compatibility method for PageNavigator."""
        if self._initialized:
            return True
        
        try:
            await self.start()
            return True
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            return False
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        return {
            'initialized': self._initialized,
            'error_count': self._error_count,
            'max_errors': self._max_errors,
            'network_errors': len(self._network_errors),
            'recent_network_errors': self._network_errors[-5:] if self._network_errors else [],
            'page_load_timeout': self._page_load_timeout,
            'last_page_load_time': self._last_page_load_time,
            'is_logged_in': self.is_logged_in,
            'current_page_type': self.current_page_type
        }
    
    def reset_error_count(self) -> None:
        """Reset error counter."""
        self._error_count = 0
        logger.debug("Error count reset")
    
    async def ensure_page_ready(self, timeout: int = 30000) -> bool:
        """Ensure page is fully loaded and ready."""
        if not self.page:
            return False
        
        try:
            # Wait for page to be in ready state
            await self.page.wait_for_load_state("domcontentloaded", timeout=timeout)
            await self.page.wait_for_load_state("networkidle", timeout=timeout)
            
            # Check and close any fancybox overlays
            await self.close_fancybox_overlay()
            
            # Verify page is responsive
            ready_state = await self.page.evaluate("() => document.readyState")
            if ready_state != "complete":
                logger.warning(f"Page not fully ready: {ready_state}")
            
            self._last_page_load_time = asyncio.get_event_loop().time()
            return True
            
        except Exception as e:
            logger.error(f"Page readiness check failed: {e}")
            return False
    
    async def close_fancybox_overlay(self) -> bool:
        """檢查並關閉 fancybox overlay 廣告彈出框。
        
        Returns:
            bool: 是否找到並關閉了彈出框
        """
        if not self.page:
            return False
            
        try:
            # Check if fancybox overlay is present
            fancybox_content = await self.page.query_selector("#fancybox-content")
            if fancybox_content:
                logger.debug("🔍 檢測到 fancybox overlay，嘗試關閉...")
                
                # Method 1: Try to find and click the close button
                close_selectors = [
                    "#fancybox-close",
                    ".fancybox-close",
                    "#fancybox-overlay .close",
                    "[title*='close']",
                    "[alt*='close']",
                    "a[title='Close']"
                ]
                
                for selector in close_selectors:
                    try:
                        close_button = await self.page.query_selector(selector)
                        if close_button:
                            logger.debug(f"找到關閉按鈕: {selector}")
                            await close_button.click()
                            await asyncio.sleep(1)
                            
                            # Check if overlay is gone
                            fancybox_after = await self.page.query_selector("#fancybox-content")
                            if not fancybox_after:
                                logger.debug("✅ 成功通過關閉按鈕關閉 fancybox overlay")
                                return True
                    except:
                        continue
                
                # Method 2: Click outside the fancybox content area
                try:
                    # Get the overlay element (usually covers the whole page)
                    overlay = await self.page.query_selector("#fancybox-overlay")
                    if overlay:
                        logger.debug("嘗試點擊 fancybox overlay 外部區域...")
                        # Get overlay bounding box and click at edge
                        box = await overlay.bounding_box()
                        if box:
                            # Click at top-left corner of overlay (outside content)
                            await self.page.mouse.click(box['x'] + 10, box['y'] + 10)
                            await asyncio.sleep(1)
                            
                            # Check if overlay is gone
                            fancybox_after = await self.page.query_selector("#fancybox-content")
                            if not fancybox_after:
                                logger.debug("✅ 成功通過點擊外部區域關閉 fancybox overlay")
                                return True
                except:
                    pass
                
                # Method 3: Press Escape key
                try:
                    logger.debug("嘗試按 Escape 鍵關閉 fancybox overlay...")
                    await self.page.keyboard.press("Escape")
                    await asyncio.sleep(1)
                    
                    # Check if overlay is gone
                    fancybox_after = await self.page.query_selector("#fancybox-content")
                    if not fancybox_after:
                        logger.debug("✅ 成功通過 Escape 鍵關閉 fancybox overlay")
                        return True
                except:
                    pass
                
                # Method 4: Use JavaScript to force close
                try:
                    logger.debug("嘗試使用 JavaScript 強制關閉 fancybox overlay...")
                    await self.page.evaluate("""
                        // Try various methods to close fancybox
                        if (typeof $.fancybox !== 'undefined') {
                            $.fancybox.close();
                        }
                        
                        // Remove elements directly
                        const fancyboxContent = document.getElementById('fancybox-content');
                        if (fancyboxContent) {
                            const parent = fancyboxContent.parentElement;
                            if (parent) parent.remove();
                        }
                        
                        const fancyboxOverlay = document.getElementById('fancybox-overlay');
                        if (fancyboxOverlay) {
                            fancyboxOverlay.remove();
                        }
                        
                        // Also try to remove any fancybox-related elements
                        const fancyboxElements = document.querySelectorAll('[id*="fancybox"], [class*="fancybox"]');
                        fancyboxElements.forEach(el => el.remove());
                    """)
                    await asyncio.sleep(1)
                    
                    # Check if overlay is gone
                    fancybox_after = await self.page.query_selector("#fancybox-content")
                    if not fancybox_after:
                        logger.debug("✅ 成功通過 JavaScript 關閉 fancybox overlay")
                        return True
                except:
                    pass
                
                logger.warning("⚠️ 無法關閉 fancybox overlay，可能會影響頁面操作")
                return False
            
            # No fancybox found
            return False
            
        except Exception as e:
            logger.debug(f"檢查 fancybox overlay 時出錯: {e}")
            return False 