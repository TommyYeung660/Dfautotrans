"""Market operations module for Dead Frontier Auto Trading System."""

import asyncio
import re
import random
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from loguru import logger

from ..config.settings import Settings
from ..automation.browser_manager import BrowserManager
from ..core.page_navigator import PageNavigator
from ..data.models import MarketItemData, SellingSlotsStatus, TradeType


class MarketOperations:
    """Dead Frontier 市場操作管理器"""
    
    def __init__(self, settings: Settings, browser_manager: BrowserManager, page_navigator: PageNavigator):
        self.settings = settings
        self.browser_manager = browser_manager
        self.page_navigator = page_navigator
        self.logger = logging.getLogger(__name__)
        
        # 緩存機制
        self._cache = {}
        self._cache_timestamp = None
        
        # 會話狀態追蹤 - 新增
        self._current_page_state = {
            'is_on_marketplace': False,
            'current_tab': None,  # 'buy' or 'sell'
            'last_navigation': None
        }
        
        logger.info("Market operations manager initialized")
        
        # Cache for market data
        self._market_cache: List[MarketItemData] = []
        self._cache_duration = 60  # seconds
        
        # 載入交易配置
        from ..config.trading_config import TradingConfigManager
        self.config_manager = TradingConfigManager()
        self.trading_config = self.config_manager.load_config()
        
        # 向後兼容的搜索配置
        self.search_config = {
            'max_price_per_unit': self.trading_config.market_search.max_price_per_unit,
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
    
    async def _ensure_marketplace_session(self, required_tab: str = None) -> bool:
        """
        確保處於市場頁面會話狀態，避免重複導航
        
        Args:
            required_tab: 需要的標籤頁 ('buy' 或 'sell')，None表示不切換標籤
            
        Returns:
            bool: 是否成功確保會話狀態
        """
        try:
            current_url = self.page.url
            
            # 檢查是否已在市場頁面
            if "page=35" in current_url:
                self._current_page_state['is_on_marketplace'] = True
                logger.debug("✅ 已在市場頁面，無需重新導航")
            else:
                # 需要導航到市場頁面
                logger.debug("🔄 導航到市場頁面...")
                if not await self.page_navigator.navigate_to_marketplace():
                    logger.error("❌ 無法導航到市場頁面")
                    return False
                self._current_page_state['is_on_marketplace'] = True
                self._current_page_state['current_tab'] = None  # 重置標籤狀態
            
            # 如果需要特定標籤，則切換
            if required_tab and self._current_page_state['current_tab'] != required_tab:
                if required_tab == 'buy':
                    success = await self._ensure_buy_tab_active()
                elif required_tab == 'sell':
                    success = await self._ensure_sell_tab_active()
                else:
                    logger.warning(f"⚠️ 未知的標籤類型: {required_tab}")
                    return False
                
                if success:
                    self._current_page_state['current_tab'] = required_tab
                    logger.debug(f"✅ 成功切換到 {required_tab} 標籤")
                else:
                    logger.error(f"❌ 切換到 {required_tab} 標籤失敗")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 確保市場會話狀態失敗: {e}")
            return False

    async def scan_market_items(self, search_term: Optional[str] = None, max_items: int = 50) -> List[MarketItemData]:
        """掃描市場物品（優化版）"""
        try:
            logger.info(f"🔍 開始掃描市場物品 (搜索詞: {search_term}, 最多: {max_items})")
            
            # 確保在購買標籤頁
            if not await self._ensure_marketplace_session('buy'):
                return []
            
            # 其餘邏輯保持不變
            await asyncio.sleep(2)
            await self.browser_manager.close_fancybox_overlay()
            
            # 執行搜索
            if search_term:
                if not await self._perform_search(search_term):
                    logger.warning("⚠️ 搜索失敗，使用默認結果")
            
            # 掃描物品
            items = await self._scan_marketplace_table(max_items)
            logger.info(f"✅ 掃描完成，找到 {len(items)} 個物品")
            return items
            
        except Exception as e:
            logger.error(f"❌ 掃描市場物品失敗: {e}")
            return []

    async def execute_purchase(self, item: MarketItemData, max_retries: int = 3) -> bool:
        """執行購買操作（優化版）"""
        try:
            logger.info(f"🛒 嘗試購買: {item.item_name} - 價格: ${item.price} - 數量: {item.quantity}")
            
            # 確保在購買標籤頁（不會重複導航）
            if not await self._ensure_marketplace_session('buy'):
                return False
            
            # 其餘購買邏輯保持不變...
            for attempt in range(max_retries):
                try:
                    await asyncio.sleep(1)
                    await self.browser_manager.close_fancybox_overlay()
                    
                    if await self._find_and_click_buy_button(item):
                        if await self._handle_purchase_confirmation():
                            logger.info(f"✅ 購買成功: {item.item_name}")
                            return True
                    
                    if attempt < max_retries - 1:
                        logger.warning(f"⚠️ 購買嘗試 {attempt + 1} 失敗，重試...")
                        await asyncio.sleep(2)
                        
                except Exception as e:
                    logger.warning(f"⚠️ 購買嘗試 {attempt + 1} 出錯: {e}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2)
            
            logger.error(f"❌ 購買失敗: {item.item_name}")
            return False
            
        except Exception as e:
            logger.error(f"❌ 購買操作失敗: {e}")
            return False

    async def list_item_for_sale(self, item_name: str, price: float, quantity: int = 1) -> bool:
        """上架物品銷售（優化版）"""
        try:
            logger.info(f"📝 準備上架銷售: {item_name} (總價: ${price})")
            
            # 確保在銷售標籤頁（不會重複導航）
            if not await self._ensure_marketplace_session('sell'):
                return False
            
            await asyncio.sleep(1)  # 減少等待時間
            await self.browser_manager.close_fancybox_overlay()
            
            # 其餘上架邏輯保持不變...
            item_info = await self._find_inventory_item(item_name)
            if not item_info:
                logger.error(f"❌ 在庫存中找不到物品: {item_name}")
                return False
            
            item_element = item_info['element']
            actual_quantity = item_info['quantity']
            
            logger.debug(f"✅ 找到庫存物品: {item_name} (數量: {actual_quantity})")
            
            # 價格計算邏輯保持不變
            if price < 100 and actual_quantity > 1:
                logger.warning(f"⚠️ 檢測到可能的單價輸入 (${price})，重新計算總價...")
                total_price = price * actual_quantity
                logger.info(f"💰 重新計算: ${price} × {actual_quantity} = ${total_price}")
                price = total_price
            
            # 執行上架操作
            if await self._execute_listing_process(item_element, price):
                logger.info(f"✅ 成功上架銷售: {item_name} (價格: ${price})")
                return True
            else:
                logger.error(f"❌ 上架失敗: {item_name}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 上架銷售失敗: {e}")
            return False

    async def batch_list_items_for_sale(self, sell_orders: List) -> List[bool]:
        """
        批量上架物品銷售（新功能）
        
        Args:
            sell_orders: 銷售訂單列表
            
        Returns:
            List[bool]: 每個物品的上架結果
        """
        try:
            logger.info(f"📦 開始批量上架 {len(sell_orders)} 個物品")
            
            # 一次性確保在銷售標籤頁
            if not await self._ensure_marketplace_session('sell'):
                return [False] * len(sell_orders)
            
            results = []
            successful_count = 0
            
            for i, sell_order in enumerate(sell_orders, 1):
                try:
                    logger.info(f"📝 上架第 {i}/{len(sell_orders)} 個物品: {sell_order.item.item_name}")
                    
                    # 不需要重新導航，直接執行上架
                    await asyncio.sleep(0.5)  # 短暫間隔
                    await self.browser_manager.close_fancybox_overlay()
                    
                    # 查找物品
                    item_info = await self._find_inventory_item(sell_order.item.item_name)
                    if not item_info:
                        logger.error(f"❌ 找不到物品: {sell_order.item.item_name}")
                        results.append(False)
                        continue
                    
                    # 執行上架
                    if await self._execute_listing_process(item_info['element'], sell_order.selling_price):
                        logger.info(f"✅ 第 {i} 個物品上架成功: {sell_order.item.item_name}")
                        results.append(True)
                        successful_count += 1
                    else:
                        logger.error(f"❌ 第 {i} 個物品上架失敗: {sell_order.item.item_name}")
                        results.append(False)
                    
                    # 短暫間隔避免操作過快
                    if i < len(sell_orders):
                        await asyncio.sleep(1)
                        
                except Exception as e:
                    logger.error(f"❌ 上架第 {i} 個物品時出錯: {e}")
                    results.append(False)
            
            logger.info(f"📦 批量上架完成: {successful_count}/{len(sell_orders)} 成功")
            return results
            
        except Exception as e:
            logger.error(f"❌ 批量上架失敗: {e}")
            return [False] * len(sell_orders)

    async def _execute_listing_process(self, item_element, price: float) -> bool:
        """執行單個物品的上架流程"""
        try:
            # 點擊空白區域清除菜單
            try:
                game_content = await self.page.query_selector("#gamecontent")
                if game_content:
                    await game_content.click()
                    await asyncio.sleep(0.3)
            except:
                pass
            
            # 右鍵點擊物品
            logger.debug("🖱️ 右鍵點擊庫存位置...")
            await item_element.click(button="right")
            await asyncio.sleep(1)
            
            # 點擊Sell按鈕
            sell_button = await self._find_sell_button()
            if not sell_button:
                logger.error("❌ 找不到Sell按鈕")
                return False
            
            await sell_button.click()
            await asyncio.sleep(1.5)
            
            # 輸入價格
            if not await self._input_selling_price(price):
                return False
            
            # 確認上架
            if not await self._confirm_listing():
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 執行上架流程失敗: {e}")
            return False

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
            # Close any blocking overlays first
            await self.browser_manager.close_fancybox_overlay()
            await asyncio.sleep(0.5)
            
            # Look for selling tab
            sell_tab = await self.page.query_selector("#loadSelling")
            if sell_tab:
                is_disabled = await sell_tab.is_disabled()
                if is_disabled:
                    logger.debug("銷售標籤頁已激活")
                    return True
                
                # Click sell tab to activate
                logger.debug("切換到銷售標籤頁...")
                try:
                    await sell_tab.click()
                except Exception as click_error:
                    logger.debug(f"普通點擊失敗，嘗試強制點擊: {click_error}")
                    await sell_tab.click(force=True)
                
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
        """在庫存中找到指定物品。基於實際DOM結構: #inventory table中的.validSlot td"""
        try:
            logger.debug(f"🔍 尋找庫存物品: '{item_name}'")
            
            # 使用配置映射獲取物品的data-type ID
            from src.dfautotrans.config.trading_config import config_manager
            target_item_id = config_manager.get_item_id_by_name(item_name)
            
            if not target_item_id:
                logger.warning(f"❌ 在配置映射中找不到物品ID: '{item_name}'")
                return None
            
            logger.debug(f"🎯 物品映射: '{item_name}' -> '{target_item_id}'")
            
            # Close any blocking overlays first
            await self.browser_manager.close_fancybox_overlay()
            await asyncio.sleep(0.5)
            
            # 根據實際DOM結構查找庫存表格
            inventory_table = await self.page.query_selector("#inventory")
            if not inventory_table:
                logger.error("❌ 找不到庫存表格 #inventory")
                return None
            
            logger.debug("✅ 找到庫存表格 #inventory")
            
            # 查找所有庫存槽位
            inventory_slots = await inventory_table.query_selector_all("td.validSlot")
            logger.debug(f"找到 {len(inventory_slots)} 個庫存槽位")
            
            # 過濾出有物品的槽位
            slots_with_items = []
            for slot in inventory_slots:
                item_div = await slot.query_selector("div.item")
                if item_div:
                    slots_with_items.append(slot)
            
            logger.debug(f"其中 {len(slots_with_items)} 個槽位有物品")
            
            for slot in slots_with_items:
                try:
                    # 查找td內的.item div
                    item_div = await slot.query_selector("div.item")
                    if not item_div:
                        continue
                    
                    # 獲取物品屬性
                    data_type = await item_div.get_attribute("data-type")
                    data_itemtype = await item_div.get_attribute("data-itemtype")
                    data_quantity = await item_div.get_attribute("data-quantity")
                    
                    logger.debug(f"檢查物品: data-type='{data_type}', data-itemtype='{data_itemtype}', quantity='{data_quantity}'")
                    
                    # 使用配置映射匹配物品
                    if data_type == target_item_id:
                        # 確保數量是整數
                        try:
                            quantity = int(data_quantity) if data_quantity else 1
                        except (ValueError, TypeError):
                            quantity = 1
                        logger.debug(f"✅ 找到匹配物品: '{item_name}' (data-type='{data_type}', quantity={quantity})")
                        return {'element': slot, 'quantity': quantity}
                    
                except Exception as slot_error:
                    logger.debug(f"檢查庫存位置時出錯: {slot_error}")
                    continue
            
            logger.warning(f"❌ 在庫存中找不到物品: '{item_name}' (data-type: '{target_item_id}')")
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

    async def _find_sell_button(self):
        """尋找Sell按鈕"""
        try:
            logger.debug("🔍 尋找Sell按鈕...")
            
            # 方法1: 直接查找width: 100%的按鈕
            width_100_buttons = await self.page.query_selector_all("button[style*='width: 100%']")
            for button in width_100_buttons:
                try:
                    text = await button.inner_text()
                    if text and text.strip().lower() == 'sell':
                        is_visible = await button.is_visible()
                        if is_visible:
                            logger.debug("✅ 找到Sell按鈕（width: 100%）")
                            return button
                except:
                    continue
            
            # 方法2: 查找絕對定位菜單中的按鈕
            context_menus = await self.page.query_selector_all("div[style*='position: absolute'][style*='background-color: black']")
            for menu in context_menus:
                try:
                    is_visible = await menu.is_visible()
                    if not is_visible:
                        continue
                        
                    menu_buttons = await menu.query_selector_all("button")
                    for button in menu_buttons:
                        text = await button.inner_text()
                        if text and text.strip().lower() == 'sell':
                            logger.debug("✅ 在右鍵菜單中找到Sell按鈕")
                            return button
                except:
                    continue
            
            # 方法3: 備用方案 - 查找所有可見的Sell按鈕
            all_buttons = await self.page.query_selector_all("button")
            for button in all_buttons:
                try:
                    text = await button.inner_text()
                    if text and text.strip().lower() == 'sell':
                        is_visible = await button.is_visible()
                        if is_visible:
                            logger.debug("✅ 找到Sell按鈕（備用方案）")
                            return button
                except:
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"❌ 尋找Sell按鈕失敗: {e}")
            return None

    async def _input_selling_price(self, price: float) -> bool:
        """輸入銷售價格"""
        try:
            logger.debug("⏳ 等待價格輸入對話框...")
            await asyncio.sleep(2)
            
            # 等待#prompt對話框出現
            prompt_dialog = await self.page.query_selector("#prompt")
            if not prompt_dialog:
                logger.error("❌ 找不到價格輸入對話框 #prompt")
                return False
            
            logger.debug("✅ 找到價格輸入對話框 #prompt")
            
            # 尋找價格輸入框: input[data-type="price"].moneyField
            price_input = await prompt_dialog.query_selector("input[data-type='price'].moneyField")
            if not price_input:
                # 備用方案
                price_input = await prompt_dialog.query_selector("input[type='number']")
            
            if not price_input:
                logger.error("❌ 找不到價格輸入框")
                return False
            
            # 清空並輸入價格（重要：每次都要重新輸入）
            logger.debug(f"💰 輸入價格: ${price}")
            await price_input.click()
            await price_input.fill("")  # 清空舊價格
            await asyncio.sleep(0.5)
            await price_input.type(str(int(price)))
            await asyncio.sleep(1)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 輸入價格失敗: {e}")
            return False

    async def _confirm_listing(self) -> bool:
        """確認上架"""
        try:
            # Step 1: 點擊第一個Yes按鈕
            logger.debug("🔍 尋找第一個Yes按鈕...")
            
            prompt_dialog = await self.page.query_selector("#prompt")
            if not prompt_dialog:
                logger.error("❌ 找不到確認對話框")
                return False
            
            # 在#prompt對話框中查找Yes按鈕
            yes_buttons = await prompt_dialog.query_selector_all("button")
            first_yes_button = None
            
            for button in yes_buttons:
                try:
                    text = await button.inner_text()
                    if text and text.strip().lower() == 'yes':
                        first_yes_button = button
                        logger.debug("✅ 找到第一個Yes按鈕")
                        break
                except:
                    continue
            
            if not first_yes_button:
                logger.error("❌ 找不到第一個Yes按鈕")
                return False
            
            # 點擊第一個Yes按鈕
            logger.debug("✅ 點擊第一個Yes按鈕...")
            await first_yes_button.click()
            await asyncio.sleep(2)
            
            # Step 2: 等待最終確認對話框並點擊第二個Yes按鈕
            logger.debug("⏳ 等待最終確認對話框...")
            await asyncio.sleep(1)
            
            # 再次查找#prompt對話框（現在是最終確認）
            final_prompt = await self.page.query_selector("#prompt")
            if not final_prompt:
                logger.warning("⚠️ 沒有找到最終確認對話框，可能已經成功")
                return True
            
            # 查找最終確認的Yes按鈕
            final_yes_buttons = await final_prompt.query_selector_all("button")
            final_yes_button = None
            
            for button in final_yes_buttons:
                try:
                    text = await button.inner_text()
                    if text and text.strip().lower() == 'yes':
                        final_yes_button = button
                        logger.debug("✅ 找到最終確認Yes按鈕")
                        break
                except:
                    continue
            
            if final_yes_button:
                logger.debug("✅ 點擊最終確認Yes按鈕...")
                await final_yes_button.click()
                await asyncio.sleep(2)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 確認上架失敗: {e}")
            return False
 