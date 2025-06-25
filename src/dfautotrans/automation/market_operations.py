"""Market operations module for Dead Frontier Auto Trading System."""

import asyncio
import re
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from loguru import logger

from ..config.settings import Settings
from ..automation.browser_manager import BrowserManager
from ..core.page_navigator import PageNavigator
from ..data.models import MarketItemData, SellingSlotsStatus, TradeType


class MarketOperations:
    """Handles all marketplace operations including scanning, buying, and selling."""
    
    def __init__(self, settings: Settings, browser_manager: BrowserManager, page_navigator: PageNavigator):
        self.settings = settings
        self.browser_manager = browser_manager
        self.page_navigator = page_navigator
        
        # Cache for market data
        self._market_cache: List[MarketItemData] = []
        self._cache_timestamp: Optional[datetime] = None
        self._cache_duration = 60  # seconds
        
        # 載入交易配置
        from ..config.trading_config import TradingConfigManager
        self.config_manager = TradingConfigManager()
        self.trading_config = self.config_manager.get_config()
        
        # 向後兼容的搜索配置
        self.search_config = {
            'max_price_per_unit': self.trading_config.buying.max_price_per_unit,
            'target_items': self.trading_config.market_search.target_items,
            'max_rows_to_check': 20,
            'auto_buy_enabled': False,
            'primary_search_terms': self.trading_config.market_search.primary_search_terms
        }
    
    @property
    def page(self):
        """動態獲取當前page對象"""
        if not self.browser_manager.page:
            raise RuntimeError("Browser page not initialized")
        return self.browser_manager.page
    
    async def scan_market_items(self, search_term: Optional[str] = None, max_items: int = 50) -> List[MarketItemData]:
        """掃描市場物品並返回可購買的物品列表。
        
        Args:
            search_term: 搜索關鍵詞，如果為None則掃描所有物品
            max_items: 最大掃描物品數量
            
        Returns:
            List[MarketItemData]: 市場物品列表
        """
        try:
            logger.info(f"🔍 開始掃描市場物品 (搜索詞: {search_term}, 最多: {max_items})")
            
            # Navigate to marketplace
            if not await self.page_navigator.navigate_to_marketplace():
                logger.error("❌ 無法導航到市場頁面")
                return []
            
            # Check and close any fancybox overlay that might be blocking the page
            await self.browser_manager.close_fancybox_overlay()
            
            # Ensure we're on the buying tab
            await self._ensure_buy_tab_active()
            
            # Perform search to load items (Dead Frontier requires keywords)
            if search_term:
                await self._perform_search(search_term)
            else:
                # 使用配置中的主要搜索詞，而不是廣泛的 'a' 搜索
                primary_terms = self.trading_config.market_search.primary_search_terms
                search_term_to_use = primary_terms[0] if primary_terms else "12.7"
                logger.info(f"🎯 沒有指定搜索詞，使用配置的主要目標搜索詞: '{search_term_to_use}'")
                await self._perform_search(search_term_to_use)
            
            # Scan market items
            items = await self._scan_marketplace_table(max_items)
            
            logger.info(f"✅ 掃描完成，找到 {len(items)} 個物品")
            
            # Update cache
            self._market_cache = items
            self._cache_timestamp = datetime.utcnow()
            
            return items
            
        except Exception as e:
            logger.error(f"❌ 掃描市場物品時出錯: {e}")
            return []
    
    async def get_selling_slots_status(self) -> Optional[SellingSlotsStatus]:
        """獲取當前銷售位狀態。
        
        Returns:
            SellingSlotsStatus: 銷售位狀態信息
        """
        try:
            logger.info("📊 檢查銷售位狀態...")
            
            # Navigate to marketplace
            if not await self.page_navigator.navigate_to_marketplace():
                logger.error("❌ 無法導航到市場頁面")
                return None
            
            # Switch to selling tab
            await self._ensure_sell_tab_active()
            
            # Extract selling slots information
            slots_info = await self._extract_selling_slots_info()
            
            if slots_info:
                status = SellingSlotsStatus(
                    current_listings=slots_info['used'],
                    max_slots=slots_info['max'],
                    listed_items=slots_info['items']
                )
                logger.info(f"✅ 銷售位狀態: {status.current_listings}/{status.max_slots}")
                return status
            
            logger.warning("⚠️ 無法獲取銷售位狀態")
            return None
            
        except Exception as e:
            logger.error(f"❌ 獲取銷售位狀態時出錯: {e}")
            return None
    
    async def execute_purchase(self, item: MarketItemData, max_retries: int = 3) -> bool:
        """執行購買操作。
        
        Args:
            item: 要購買的物品
            max_retries: 最大重試次數
            
        Returns:
            bool: 購買是否成功
        """
        try:
            logger.info(f"💰 準備購買: {item.item_name} (價格: ${item.price}, 賣家: {item.seller})")
            
            # Navigate to marketplace if not already there
            current_url = self.page.url
            if "page=35" not in current_url:
                if not await self.page_navigator.navigate_to_marketplace():
                    logger.error("❌ 無法導航到市場頁面")
                    return False
            
            # Check and close any fancybox overlay before purchase
            await self.browser_manager.close_fancybox_overlay()
            
            # Ensure we're on the buying tab
            await self._ensure_buy_tab_active()
            
            # Find the item in the marketplace table
            success = False
            for attempt in range(max_retries):
                logger.info(f"🔄 購買嘗試 {attempt + 1}/{max_retries}")
                
                # Look for the specific item
                item_found = await self._find_and_click_buy_button(item)
                
                if not item_found:
                    logger.warning(f"⚠️ 第{attempt + 1}次嘗試：找不到指定物品")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2)
                        continue
                    break
                
                # Handle confirmation dialog
                purchase_confirmed = await self._handle_purchase_confirmation()
                
                if purchase_confirmed:
                    logger.info(f"✅ 成功購買: {item.item_name}")
                    success = True
                    break
                else:
                    logger.warning(f"⚠️ 第{attempt + 1}次嘗試：購買確認失敗")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(3)
            
            return success
            
        except Exception as e:
            logger.error(f"❌ 購買物品時出錯: {e}")
            return False
    
    async def list_item_for_sale(self, item_name: str, price: float, quantity: int = 1) -> bool:
        """將物品上架銷售。
        
        Args:
            item_name: 物品名稱
            price: 銷售價格
            quantity: 數量（暫時不支援部分銷售）
            
        Returns:
            bool: 上架是否成功
        """
        try:
            logger.info(f"📝 準備上架銷售: {item_name} (價格: ${price})")
            
            # Navigate to marketplace
            if not await self.page_navigator.navigate_to_marketplace():
                logger.error("❌ 無法導航到市場頁面")
                return False
            
            # Switch to selling tab
            await self._ensure_sell_tab_active()
            
            # Find the item in inventory
            item_element = await self._find_inventory_item(item_name)
            if not item_element:
                logger.error(f"❌ 在庫存中找不到物品: {item_name}")
                return False
            
            # Right-click on item to open context menu
            await item_element.click(button="right")
            await asyncio.sleep(1)
            
            # Click "Sell" option
            sell_option = await self.page.query_selector("text=/sell/i")
            if not sell_option:
                logger.error("❌ 找不到銷售選項")
                return False
            
            await sell_option.click()
            await asyncio.sleep(1)
            
            # Enter price
            price_input = await self.page.query_selector("input[name='price'], #sellPrice, .price-input")
            if not price_input:
                logger.error("❌ 找不到價格輸入框")
                return False
            
            await price_input.fill(str(price))
            await asyncio.sleep(0.5)
            
            # Confirm sale
            confirm_button = await self.page.query_selector("input[type='submit'], button:has-text('Confirm'), .confirm-button")
            if not confirm_button:
                logger.error("❌ 找不到確認按鈕")
                return False
            
            await confirm_button.click()
            await asyncio.sleep(2)
            
            logger.info(f"✅ 成功上架銷售: {item_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 上架物品時出錯: {e}")
            return False
    
    async def get_market_summary(self) -> Dict[str, Any]:
        """獲取市場概要信息。
        
        Returns:
            Dict: 市場概要信息
        """
        try:
            items = await self.scan_market_items()
            selling_status = await self.get_selling_slots_status()
            
            # Analyze items
            item_count = len(items)
            avg_price = sum(item.price for item in items) / item_count if item_count > 0 else 0
            price_range = (min(item.price for item in items), max(item.price for item in items)) if item_count > 0 else (0, 0)
            
            # Group by item type
            item_types = {}
            for item in items:
                if item.item_name not in item_types:
                    item_types[item.item_name] = []
                item_types[item.item_name].append(item)
            
            summary = {
                'total_items': item_count,
                'average_price': round(avg_price, 2),
                'price_range': price_range,
                'item_types': {name: len(items) for name, items in item_types.items()},
                'selling_slots': {
                    'used': selling_status.current_listings if selling_status else 0,
                    'max': selling_status.max_slots if selling_status else 30,
                    'available': selling_status.available_slots if selling_status else 30
                },
                'scan_timestamp': datetime.utcnow().isoformat()
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"❌ 獲取市場概要時出錯: {e}")
            return {}
    
    # Private helper methods
    
    async def _ensure_buy_tab_active(self) -> bool:
        """確保購買標籤頁是激活狀態。"""
        try:
            # Check if buy tab is already active
            buy_tab = await self.page.query_selector("#loadBuying")
            if buy_tab:
                is_disabled = await buy_tab.is_disabled()
                if is_disabled:
                    logger.debug("購買標籤頁已激活")
                    return True
                
                # Click buy tab to activate
                logger.debug("切換到購買標籤頁...")
                await buy_tab.click()
                await asyncio.sleep(2)
                return True
            
            logger.warning("找不到購買標籤頁")
            return False
            
        except Exception as e:
            logger.error(f"切換到購買標籤頁時出錯: {e}")
            return False
    
    async def _ensure_sell_tab_active(self) -> bool:
        """確保銷售標籤頁是激活狀態。"""
        try:
            # Look for selling tab
            sell_tab = await self.page.query_selector("#loadSelling")
            if sell_tab:
                is_disabled = await sell_tab.is_disabled()
                if is_disabled:
                    logger.debug("銷售標籤頁已激活")
                    return True
                
                # Click sell tab to activate
                logger.debug("切換到銷售標籤頁...")
                await sell_tab.click()
                await asyncio.sleep(2)
                return True
            
            logger.warning("找不到銷售標籤頁")
            return False
            
        except Exception as e:
            logger.error(f"切換到銷售標籤頁時出錯: {e}")
            return False
    
    async def _perform_search(self, search_term: str) -> bool:
        """執行市場搜索。"""
        try:
            # Check and close any fancybox overlay before search
            await self.browser_manager.close_fancybox_overlay()
            
            # Find search input field (from marketplace_helper.js: searchField)
            search_input = await self.page.query_selector("#searchField")
            if not search_input:
                logger.warning("找不到搜索輸入框 #searchField")
                return False
            
            # Clear and enter search term (empty string for loading all items)
            await search_input.fill("")
            await asyncio.sleep(0.2)
            
            if search_term:  # Type the search term
                await search_input.type(search_term)
                await asyncio.sleep(0.5)
                logger.debug(f"已輸入搜索詞: '{search_term}'")
            else:
                logger.warning("搜索詞為空，這可能不會返回結果")
                await asyncio.sleep(0.3)
            
            # Find and click search button (from marketplace_helper.js: makeSearch)
            search_button = await self.page.query_selector("#makeSearch")
            if search_button:
                logger.debug("找到搜索按鈕")
                
                # Always enable search button first (required by Dead Frontier's JavaScript)
                await self.page.evaluate("document.getElementById('makeSearch').disabled = false")
                await asyncio.sleep(0.2)
                
                # Verify button is enabled
                is_disabled = await search_button.is_disabled()
                if is_disabled:
                    logger.error("無法啟用搜索按鈕")
                    return False
                else:
                    logger.debug("搜索按鈕已啟用，點擊...")
                
                # Click the search button
                await search_button.click()
                logger.debug("搜索按鈕已點擊")
                await asyncio.sleep(5)  # Wait longer for search results to load
                
                # Verify search was executed by checking for results
                item_display = await self.page.query_selector("#itemDisplay")
                if item_display:
                    logger.debug("搜索完成，找到物品顯示區域")
                else:
                    logger.warning("搜索後沒有找到物品顯示區域")
                    
            else:
                logger.warning("找不到搜索按鈕 #makeSearch，嘗試按Enter鍵")
                # Fallback to Enter key
                await search_input.press("Enter")
                await asyncio.sleep(3)
            
            logger.debug(f"搜索完成: {search_term if search_term else '(全部物品)'}")
            
            # Debug: Check if items loaded after search
            fake_items_count = len(await self.page.query_selector_all(".fakeItem"))
            logger.debug(f"搜索完成後找到 {fake_items_count} 個 .fakeItem 元素")
            
            return True
            
        except Exception as e:
            logger.error(f"執行搜索時出錯: {e}")
            return False
    
    async def _scan_marketplace_table(self, max_items: int) -> List[MarketItemData]:
        """掃描市場表格並提取物品信息。"""
        try:
            items = []
            
            # Wait for items to load after search
            await asyncio.sleep(3)
            
            # Check if itemDisplay container exists (from marketplace_helper.js)
            item_display = await self.page.query_selector("#itemDisplay")
            if not item_display:
                logger.warning("找不到物品顯示容器 #itemDisplay")
                return items
            
            # Find marketplace items using .fakeItem selector (from marketplace_helper.js)
            rows = await self.page.query_selector_all(".fakeItem")
            
            if not rows:
                logger.warning("找不到市場物品 (.fakeItem)")
                # Try alternative selectors as fallback
                alternative_selectors = [
                    ".marketItem",
                    ".item-row", 
                    "tr[class*='item']",
                    "#itemDisplay > div",
                    "#itemDisplay tr"
                ]
                
                for selector in alternative_selectors:
                    rows = await self.page.query_selector_all(selector)
                    if rows:
                        logger.debug(f"使用備用選擇器找到 {len(rows)} 行: {selector}")
                        break
                
                if not rows:
                    logger.warning("使用所有選擇器都找不到市場物品")
                    return items
            else:
                logger.debug(f"找到 {len(rows)} 個市場物品 (.fakeItem)")
            
            # Process each row
            processed_count = 0
            for i, row in enumerate(rows[:max_items]):
                try:
                    item = await self._extract_item_from_row(row, i)
                    if item:
                        items.append(item)
                        processed_count += 1
                        
                        if processed_count >= max_items:
                            break
                            
                except Exception as e:
                    logger.warning(f"處理第{i+1}行時出錯: {e}")
                    continue
            
            logger.info(f"成功提取 {len(items)} 個物品信息")
            return items
            
        except Exception as e:
            logger.error(f"掃描市場表格時出錯: {e}")
            return []
    
    async def _extract_item_from_row(self, row, row_index: int) -> Optional[MarketItemData]:
        """從市場物品行中提取物品信息。"""
        try:
            # Extract data attributes (from actual DOM structure)
            price = float(await row.get_attribute("data-price") or "0")
            quantity = int(await row.get_attribute("data-quantity") or "1")
            
            # Calculate price per unit
            price_per_unit = price / quantity if quantity > 0 else price
            
            # Extract item name from .itemName div
            item_name_element = await row.query_selector(".itemName")
            if item_name_element:
                item_name = (await item_name_element.inner_text()).strip()
            else:
                item_name = f"Unknown Item {row_index}"
            
            # Extract seller from .seller a tag
            seller_element = await row.query_selector(".seller")
            if seller_element:
                seller = (await seller_element.inner_text()).strip()
            else:
                seller = f"Unknown Seller {row_index}"
            
            # Extract trade zone from .tradeZone div
            trade_zone_element = await row.query_selector(".tradeZone")
            trade_zone = await trade_zone_element.inner_text() if trade_zone_element else None
            
            # Get buy button attributes
            buy_button = await row.query_selector("button[data-action='buyItem']")
            buy_item_location = None
            buy_num = None
            if buy_button:
                buy_item_location = await buy_button.get_attribute("data-item-location")
                buy_num = await buy_button.get_attribute("data-buynum")
            
            # Validate data
            if not item_name or price <= 0:
                logger.debug(f"跳過無效物品數據: name='{item_name}', price={price}")
                return None
            
            item = MarketItemData(
                item_name=item_name,
                seller=seller,
                trade_zone=trade_zone,
                price=price_per_unit,  # Use price per unit for comparison
                quantity=quantity,
                buy_item_location=buy_item_location,
                buy_num=buy_num
            )
            
            logger.debug(f"提取物品: {item.item_name} - ${item.price}/單位 (總量: {quantity}, 賣家: {item.seller})")
            return item
            
        except Exception as e:
            logger.warning(f"提取第{row_index+1}行物品信息時出錯: {e}")
            return None
    
    async def _find_and_click_buy_button(self, item: MarketItemData) -> bool:
        """找到指定物品並點擊購買按鈕。"""
        try:
            # 首先關閉可能阻擋的信息框
            await self._close_info_box()
            
            # Find all market rows (.fakeItem from marketplace_helper.js)
            rows = await self.page.query_selector_all(".fakeItem")
            
            for row in rows:
                # Check if this row matches our item using data attributes
                if await self._is_matching_item_row(row, item):
                    # Look for buy button with data-action="buyItem" (from marketplace_helper.js)
                    buy_button = await row.query_selector("[data-action='buyItem']")
                    
                    if buy_button:
                        logger.debug(f"找到購買按鈕，準備點擊...")
                        
                        # 再次確保沒有阻擋元素
                        await self._close_info_box()
                        
                        # 使用更安全的點擊方式
                        try:
                            await buy_button.click(force=True)
                        except Exception as click_error:
                            logger.debug(f"強制點擊失敗，嘗試JavaScript點擊: {click_error}")
                            # 備用方案：使用JavaScript點擊
                            await self.page.evaluate("(element) => element.click()", buy_button)
                        
                        await asyncio.sleep(1)
                        return True
                    else:
                        logger.warning(f"找到匹配物品但沒有購買按鈕")
                        return False
            
            logger.warning(f"找不到匹配的物品: {item.item_name}")
            return False
            
        except Exception as e:
            logger.error(f"查找並點擊購買按鈕時出錯: {e}")
            return False
    
    async def _close_info_box(self):
        """關閉可能阻擋點擊的信息框"""
        try:
            # 嘗試隱藏 infoBox
            info_box = await self.page.query_selector("#infoBox")
            if info_box:
                # 檢查是否可見
                is_visible = await info_box.is_visible()
                if is_visible:
                    logger.debug("發現可見的infoBox，嘗試隱藏...")
                    # 使用JavaScript強制隱藏
                    await self.page.evaluate("document.getElementById('infoBox').style.visibility = 'hidden'")
                    await asyncio.sleep(0.2)
            
            # 也檢查其他可能的阻擋元素
            blocking_selectors = ["#textAddon", ".tooltip", ".popup"]
            for selector in blocking_selectors:
                element = await self.page.query_selector(selector)
                if element:
                    is_visible = await element.is_visible()
                    if is_visible:
                        await self.page.evaluate(f"document.querySelector('{selector}').style.display = 'none'")
                        
        except Exception as e:
            logger.debug(f"關閉信息框時出錯: {e}")
            # 不拋出異常，因為這只是輔助功能
    
    async def _is_matching_item_row(self, row, target_item: MarketItemData) -> bool:
        """檢查市場物品行是否匹配目標物品。"""
        try:
            # Use data attributes for price comparison (most reliable)
            row_price = await row.get_attribute("data-price")
            row_quantity = await row.get_attribute("data-quantity")
            
            if row_price and row_quantity:
                try:
                    price_per_unit = float(row_price) / float(row_quantity)
                    # Check if price matches (with small tolerance)
                    if abs(price_per_unit - target_item.price) < 0.01:
                        # Also check item name and seller from DOM elements
                        item_name_element = await row.query_selector(".itemName")
                        seller_element = await row.query_selector(".seller")
                        
                        if item_name_element and seller_element:
                            row_item_name = (await item_name_element.inner_text()).strip()
                            row_seller = (await seller_element.inner_text()).strip()
                            
                            name_match = row_item_name == target_item.item_name
                            seller_match = row_seller == target_item.seller
                            
                            logger.debug(f"匹配檢查: 名稱={name_match} ({row_item_name} vs {target_item.item_name}), 賣家={seller_match} ({row_seller} vs {target_item.seller}), 價格匹配")
                            return name_match and seller_match
                except (ValueError, TypeError) as e:
                    logger.debug(f"價格計算錯誤: {e}")
                    pass
            
            # Fallback: Extract item info from DOM elements directly
            item_name_element = await row.query_selector(".itemName")
            seller_element = await row.query_selector(".seller")
            price_element = await row.query_selector(".salePrice")
            
            if not all([item_name_element, seller_element, price_element]):
                logger.debug("無法找到必要的DOM元素")
                return False
            
            row_item_name = (await item_name_element.inner_text()).strip()
            row_seller = (await seller_element.inner_text()).strip()
            row_price_text = await price_element.inner_text()
            row_price = self._extract_price_from_text(row_price_text)
            
            # Match criteria: name, seller, and price must match
            name_match = row_item_name == target_item.item_name
            seller_match = row_seller == target_item.seller
            price_match = abs(row_price - target_item.price) < 0.01  # Small tolerance for floating point
            
            logger.debug(f"回退匹配檢查: 名稱={name_match}, 賣家={seller_match}, 價格={price_match} ({row_price} vs {target_item.price})")
            return name_match and seller_match and price_match
            
        except Exception as e:
            logger.debug(f"檢查物品匹配時出錯: {e}")
            return False
    
    async def _handle_purchase_confirmation(self) -> bool:
        """處理購買確認對話框。"""
        try:
            # Wait for confirmation dialog to appear
            await asyncio.sleep(1)
            
            # From marketplace_helper.js: look for "Yes" button in #gamecontent popup
            try:
                # Wait for the popup to appear
                popup = await self.page.wait_for_selector("#gamecontent", timeout=5000)
                if popup:
                    logger.debug("找到確認對話框 #gamecontent")
                    
                    # Look for elements with innerHTML "Yes" (from marketplace_helper.js)
                    # Use XPath to find element with exact text "Yes"
                    yes_buttons = await self.page.query_selector_all("#gamecontent *")
                    
                    for button in yes_buttons:
                        try:
                            inner_html = await button.inner_html()
                            if inner_html.strip() == "Yes":
                                logger.debug("找到確認按鈕: innerHTML='Yes'")
                                await button.click()
                                await asyncio.sleep(2)  # Wait for purchase to process
                                return True
                        except:
                            continue
                    
                    # Also try other common selectors within the popup
                    for selector in ["input[value='Yes']", "button:has-text('Yes')", "[onclick*='yes']", "input[type='button'][value='Yes']"]:
                        try:
                            confirm_button = await popup.query_selector(selector)
                            if confirm_button:
                                logger.debug(f"找到確認按鈕: {selector}")
                                await confirm_button.click()
                                await asyncio.sleep(2)
                                return True
                        except:
                            continue
                            
                    logger.warning("在 #gamecontent 中找不到 Yes 按鈕")
            except Exception as popup_error:
                logger.warning(f"等待 #gamecontent 彈出框時出錯: {popup_error}")
            
            # Fallback: Look for various types of confirmation dialogs anywhere on page
            confirmation_selectors = [
                "input[type='button'][value*='Yes']",
                "button:has-text('Yes')",
                "input[value*='Yes']",
                "input[type='button'][value*='Confirm']",
                "button:has-text('Confirm')",
                ".confirm-button",
                ".dialog-confirm"
            ]
            
            for selector in confirmation_selectors:
                try:
                    confirm_button = await self.page.wait_for_selector(selector, timeout=2000)
                    if confirm_button:
                        logger.debug(f"找到確認按鈕: {selector}")
                        await confirm_button.click()
                        await asyncio.sleep(2)  # Wait for purchase to process
                        return True
                except:
                    continue
            
            logger.warning("沒有找到任何確認對話框")
            return False
            
        except Exception as e:
            logger.error(f"處理購買確認時出錯: {e}")
            return False
    
    async def _find_inventory_item(self, item_name: str):
        """在庫存中找到指定物品。"""
        try:
            # Look for inventory items
            inventory_items = await self.page.query_selector_all(".inventory-item, .item, [class*='inv']")
            
            for item_element in inventory_items:
                # Check item name/title
                item_text = await item_element.inner_text()
                item_title = await item_element.get_attribute("title")
                
                if (item_name.lower() in item_text.lower() or 
                    (item_title and item_name.lower() in item_title.lower())):
                    return item_element
            
            return None
            
        except Exception as e:
            logger.error(f"查找庫存物品時出錯: {e}")
            return None
    
    async def _extract_selling_slots_info(self) -> Optional[Dict[str, Any]]:
        """提取銷售位信息。"""
        try:
            # Wait for selling tab to load
            await asyncio.sleep(2)
            
            # First try to find the specific tradeSlotDisplay element
            trade_slot_display = await self.page.query_selector(".tradeSlotDisplay")
            used_slots = 0
            max_slots = 30  # Default
            
            if trade_slot_display:
                text = await trade_slot_display.inner_text()
                # Look for pattern like "2 / 26" or "6/30"
                match = re.search(r'(\d+)\s*/\s*(\d+)', text)
                if match:
                    used_slots = int(match.group(1))
                    max_slots = int(match.group(2))
                    logger.debug(f"✅ 從 .tradeSlotDisplay 找到銷售位信息: {used_slots}/{max_slots}")
                else:
                    logger.debug(f"⚠️ .tradeSlotDisplay 文本格式不匹配: '{text}'")
            else:
                logger.debug("⚠️ 找不到 .tradeSlotDisplay 元素，嘗試其他選擇器...")
                
                # Fallback: try other selectors
                slots_info_selectors = [
                    "text=/\\d+\\/\\d+/",  # Look for X/Y pattern
                    ".selling-slots-info",
                    ".marketplace-selling", 
                    "#sellingInfo",
                    "td:has-text('/')",  # Table cell with slash
                    "span:has-text('/')", # Span with slash
                    "div:has-text('/')"   # Div with slash
                ]
                
                for selector in slots_info_selectors:
                    try:
                        elements = await self.page.query_selector_all(selector)
                        for element in elements:
                            text = await element.inner_text()
                            # Look for pattern like "6/30" or "0/30"
                            match = re.search(r'(\d+)\s*/\s*(\d+)', text)
                            if match:
                                used_slots = int(match.group(1))
                                max_slots = int(match.group(2))
                                logger.debug(f"從備用選擇器找到銷售位信息: {used_slots}/{max_slots} (選擇器: {selector})")
                                break
                        if used_slots > 0 or max_slots != 30:  # Found valid info
                            break
                    except:
                        continue
            
            # If no slots info found, try to count items directly
            if used_slots == 0 and max_slots == 30:
                # Look for selling items in various possible containers
                selling_selectors = [
                    ".fakeItem",  # Items in selling tab
                    ".selling-item", 
                    ".listed-item", 
                    ".my-listing",
                    "#itemDisplay .fakeItem",  # Items in item display area
                    "tr[data-action]",  # Rows with data-action
                    "tr:has(button)"  # Rows with buttons
                ]
                
                for selector in selling_selectors:
                    try:
                        selling_items = await self.page.query_selector_all(selector)
                        if selling_items:
                            used_slots = len(selling_items)
                            logger.debug(f"通過計數找到 {used_slots} 個銷售物品 (選擇器: {selector})")
                            break
                    except:
                        continue
            
            # Get list of currently listed items
            listed_items = await self._get_listed_items()
            
            return {
                'used': used_slots,
                'max': max_slots,
                'items': listed_items
            }
            
        except Exception as e:
            logger.error(f"提取銷售位信息時出錯: {e}")
            return None
    
    async def _get_listed_items(self) -> List[str]:
        """獲取當前已上架的物品列表。"""
        try:
            items = []
            
            # Try multiple selectors to find listed items
            item_selectors = [
                ".fakeItem",  # Standard market items in selling tab
                ".selling-item", 
                ".listed-item", 
                ".my-listing",
                "#itemDisplay .fakeItem",  # Items in display area
                "tr[data-type]"  # Rows with data-type attribute
            ]
            
            for selector in item_selectors:
                try:
                    item_elements = await self.page.query_selector_all(selector)
                    
                    for element in item_elements:
                        # Try different ways to extract item name
                        item_name = None
                        
                        # Method 1: Look for .itemName class (from marketplace structure)
                        item_name_element = await element.query_selector(".itemName")
                        if item_name_element:
                            item_name = await item_name_element.inner_text()
                        
                        # Method 2: Look for data-cash attribute
                        if not item_name:
                            item_name_element = await element.query_selector("[data-cash]")
                            if item_name_element:
                                item_name = await item_name_element.get_attribute("data-cash")
                        
                        # Method 3: Try common selectors
                        if not item_name:
                            name_selectors = [".item-name", ".name", "td:first-child", ".title"]
                            for name_sel in name_selectors:
                                item_name_element = await element.query_selector(name_sel)
                                if item_name_element:
                                    item_name = await item_name_element.inner_text()
                                    break
                        
                        # Method 4: Use element text directly if it looks like an item name
                        if not item_name:
                            element_text = await element.inner_text()
                            if element_text and len(element_text.strip()) > 0 and len(element_text.strip()) < 100:
                                # Take first line as item name
                                item_name = element_text.strip().split('\n')[0]
                        
                        if item_name and item_name.strip():
                            clean_name = item_name.strip()
                            if clean_name not in items and len(clean_name) > 1:
                                items.append(clean_name)
                                logger.debug(f"找到已上架物品: {clean_name}")
                    
                    if items:  # Found items with this selector, break
                        logger.debug(f"使用選擇器 {selector} 找到 {len(items)} 個已上架物品")
                        break
                        
                except Exception as selector_error:
                    logger.debug(f"選擇器 {selector} 失敗: {selector_error}")
                    continue
            
            return items
            
        except Exception as e:
            logger.error(f"獲取已上架物品列表時出錯: {e}")
            return []
    
    def _extract_price_from_text(self, text: str) -> float:
        """從文本中提取價格數字。"""
        try:
            # Remove currency symbols and commas
            clean_text = re.sub(r'[$,]', '', text.strip())
            
            # Extract numeric value
            match = re.search(r'(\d+(?:\.\d+)?)', clean_text)
            if match:
                return float(match.group(1))
            
            return 0.0
            
        except:
            return 0.0
    
    def _extract_number_from_text(self, text: str) -> Optional[int]:
        """從文本中提取數字。"""
        try:
            match = re.search(r'(\d+)', text.strip())
            if match:
                return int(match.group(1))
            return None
        except:
            return None
    
    def _is_cache_valid(self) -> bool:
        """檢查緩存是否有效。"""
        if self._cache_timestamp is None:
            return False
        
        time_diff = (datetime.utcnow() - self._cache_timestamp).total_seconds()
        return time_diff < self._cache_duration
    
    def _clear_cache(self) -> None:
        """清除緩存。"""
        self._market_cache = []
        self._cache_timestamp = None
 