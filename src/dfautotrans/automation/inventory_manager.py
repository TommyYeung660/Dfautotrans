"""Inventory management module for Dead Frontier Auto Trading System."""

import asyncio
import re
from typing import Optional, List, Dict, Any
from datetime import datetime
from loguru import logger

from ..config.settings import Settings
from ..automation.browser_manager import BrowserManager
from ..core.page_navigator import PageNavigator
from ..data.models import InventoryItemData, SellingSlotsStatus


class InventoryItem:
    """Represents an individual inventory item."""
    
    def __init__(self, slot: int, item_type: str, item_name: str, quantity: int = 1, 
                 quality: int = 1, item_category: str = "item"):
        self.slot = slot
        self.item_type = item_type  # e.g., "127rifleammo", "freshvegetables_cooked"
        self.item_name = item_name  # e.g., "12.7 Rifle Bullets", "Cooked Fresh Vegetables"
        self.quantity = quantity
        self.quality = quality
        self.item_category = item_category  # "ammo", "item", etc.
    
    def __str__(self):
        if self.quantity > 1:
            return f"{self.item_name} x{self.quantity}"
        return self.item_name
    
    def to_dict(self):
        return {
            'slot': self.slot,
            'type': self.item_type,
            'name': self.item_name,
            'quantity': self.quantity,
            'quality': self.quality,
            'category': self.item_category
        }


class InventoryManager:
    """Handles all inventory and storage management operations."""
    
    def __init__(self, settings: Settings, browser_manager: BrowserManager, page_navigator: PageNavigator):
        self.settings = settings
        self.browser_manager = browser_manager
        self.page_navigator = page_navigator
        
        # Cache for inventory information
        self._inventory_cache: Optional[Dict[str, Any]] = None
        self._storage_cache: Optional[Dict[str, Any]] = None
        self._cache_timestamp: Optional[datetime] = None
        self._cache_duration = 30  # seconds
        
        # Item type to name mapping
        self.item_type_mapping = {
            '127rifleammo': '12.7 Rifle Bullets',
            'freshvegetables_cooked': 'Cooked Fresh Vegetables',
            'freshmeat_cooked': 'Cooked Fresh Meat',
            # Add more mappings as needed
        }
    
    @property
    def page(self):
        """動態獲取當前page對象"""
        if not self.browser_manager.page:
            raise RuntimeError("Browser page not initialized")
        return self.browser_manager.page
    
    async def get_inventory_status(self) -> Dict[str, Any]:
        """Get current inventory status with detailed item information."""
        try:
            # Navigate to storage page to access inventory info
            if not await self.page_navigator.navigate_to_storage():
                return {'used': 0, 'total': 26, 'items': []}
                
            # Extract inventory information
            inventory_info = await self._extract_inventory_info()
            if inventory_info:
                return {
                    'used': inventory_info['current'],
                    'total': inventory_info['max'],
                    'items': inventory_info['items']
                }
                
            logger.warning("無法獲取庫存狀態信息")
            return {'used': 0, 'total': 26, 'items': []}
            
        except Exception as e:
            logger.error(f"獲取庫存狀態時出錯: {e}")
            return {'used': 0, 'total': 26, 'items': []}
    
    async def get_storage_status(self) -> Dict[str, Any]:
        """Get current storage status with detailed item information."""
        try:
            # Navigate to storage page
            if not await self.page_navigator.navigate_to_storage():
                return {'used': 0, 'total': 40, 'items': []}
                
            # Extract storage information
            storage_info = await self._extract_storage_info()
            if storage_info:
                return {
                    'used': storage_info['current'],
                    'total': storage_info['max'],
                    'items': storage_info['items']
                }
                
            logger.warning("無法獲取倉庫狀態信息")
            return {'used': 0, 'total': 40, 'items': []}
            
        except Exception as e:
            logger.error(f"獲取倉庫狀態時出錯: {e}")
            return {'used': 0, 'total': 40, 'items': []}
    
    async def check_inventory_full(self) -> bool:
        """Check if inventory is full."""
        status = await self.get_inventory_status()
        if status:
            used = status.get('used', 0)
            total = status.get('total', 0)
            return used >= total
        return False
    
    async def deposit_all_to_storage(self) -> bool:
        """Deposit all inventory items to storage."""
        logger.info("📦 準備將所有庫存物品存入倉庫...")
        
        try:
            # Navigate to storage page
            if not await self.page_navigator.navigate_to_storage():
                logger.error("❌ 無法導航到倉庫頁面")
                return False
            
            # Wait for page to fully load
            await asyncio.sleep(2)
            
            # Check if inventory has items first
            inventory_status = await self.get_inventory_status()
            if inventory_status and inventory_status.get('used', 0) == 0:
                logger.info("ℹ️ 庫存為空，無需存入操作")
                return True
            
            # Get inventory status before deposit
            initial_inventory = inventory_status
            
            # Look for deposit button with improved logic
            deposit_button = None
            button_selectors = [
                "#invtostorage",  # 主要按鈕ID
                "button#invtostorage",
                "input#invtostorage",
                "[id='invtostorage']"
            ]
            
            for selector in button_selectors:
                try:
                    # Wait for element to be present
                    await self.page.wait_for_selector(selector, timeout=5000)
                    deposit_button = await self.page.query_selector(selector)
                    
                    if deposit_button:
                        # Check if button is enabled and visible
                        is_disabled = await deposit_button.is_disabled()
                        is_visible = await deposit_button.is_visible()
                        
                        if not is_disabled and is_visible:
                            logger.debug(f"找到可用的存入按鈕: {selector}")
                            break
                        else:
                            logger.warning(f"按鈕 {selector} 不可用: disabled={is_disabled}, visible={is_visible}")
                            deposit_button = None
                            
                except Exception as e:
                    logger.debug(f"查找按鈕 {selector} 失敗: {e}")
                    continue
            
            if not deposit_button:
                logger.error("❌ 找不到可用的存入所有物品按鈕")
                return False
            
            # Try multiple click methods
            click_success = False
            click_methods = [
                ("standard_click", lambda: deposit_button.click()),
                ("force_click", lambda: deposit_button.click(force=True)),
                ("js_click", lambda: deposit_button.evaluate("element => element.click()")),
                ("dispatch_click", lambda: deposit_button.dispatch_event("click"))
            ]
            
            for method_name, click_method in click_methods:
                try:
                    logger.debug(f"嘗試 {method_name} 點擊存入按鈕...")
                    await click_method()
                    logger.info(f"✅ 使用 {method_name} 成功點擊存入按鈕")
                    click_success = True
                    break
                except Exception as e:
                    logger.warning(f"❌ {method_name} 點擊失敗: {e}")
                    continue
            
            if not click_success:
                logger.error("❌ 所有點擊方法都失敗")
                return False
            
            # Wait for operation to complete with longer timeout
            logger.info("⏳ 等待存入操作完成...")
            await asyncio.sleep(5)  # 增加等待時間
            
            # Clear cache to get fresh data
            self._clear_cache()
            
            # Verify operation success with retry
            verification_attempts = 3
            for attempt in range(verification_attempts):
                try:
                    new_inventory = await self.get_inventory_status()
                    
                    if new_inventory and initial_inventory:
                        new_used = new_inventory.get('used', 0)
                        initial_used = initial_inventory.get('used', 0)
                        
                        if new_used < initial_used:
                            deposited_count = initial_used - new_used
                            logger.info(f"✅ 成功存入 {deposited_count} 件物品到倉庫")
                            return True
                        elif new_used == 0:
                            logger.info(f"✅ 成功存入所有 {initial_used} 件物品到倉庫")
                            return True
                        else:
                            if attempt < verification_attempts - 1:
                                logger.debug(f"驗證嘗試 {attempt + 1}: 庫存狀態未變化，等待...")
                                await asyncio.sleep(2)
                                continue
                            else:
                                logger.warning("⚠️ 存入操作可能未完全成功")
                                return False
                    else:
                        logger.warning("⚠️ 無法獲取驗證數據")
                        return False
                        
                except Exception as e:
                    logger.error(f"驗證嘗試 {attempt + 1} 失敗: {e}")
                    if attempt < verification_attempts - 1:
                        await asyncio.sleep(2)
                        continue
                    return False
                
        except Exception as e:
            logger.error(f"❌ 存入所有物品時出錯: {e}")
            return False
    
    async def withdraw_all_from_storage(self) -> bool:
        """從倉庫取出所有物品到庫存"""
        try:
            logger.info("開始從倉庫取出所有物品...")
            
            # 導航到倉庫頁面
            if not await self.page_navigator.navigate_to_storage():
                logger.error("無法導航到倉庫頁面")
                return False
            
            # 獲取倉庫狀態
            storage_status = await self.get_storage_status()
            if storage_status['used'] == 0:
                logger.info("倉庫為空，無需取出物品")
                return True
                
            logger.info(f"倉庫狀態: {storage_status['used']}/{storage_status['total']}")
            
            max_attempts = 10
            for attempt in range(max_attempts):
                try:
                    # 嘗試點擊取出按鈕 (#storagetoinv)
                    button = await self.page.query_selector('#storagetoinv')
                    if not button:
                        logger.error("找不到倉庫取出按鈕")
                        return False
                    
                    # 檢查按鈕是否被禁用
                    is_disabled = await button.is_disabled()
                    if is_disabled:
                        # 如果按鈕被禁用，檢查是否因為倉庫為空
                        current_storage = await self.get_storage_status()
                        if current_storage['used'] == 0:
                            logger.info("倉庫已為空，取出操作完成")
                            return True
                        else:
                            logger.warning(f"取出按鈕被禁用但倉庫仍有 {current_storage['used']} 個物品")
                            await asyncio.sleep(1)
                            continue
                    
                    # 點擊取出按鈕
                    await button.click()
                    
                    # 等待頁面更新
                    await asyncio.sleep(1)
                    
                    # 檢查是否成功
                    new_storage_status = await self.get_storage_status()
                    if new_storage_status['used'] < storage_status['used']:
                        logger.info(f"成功取出物品，倉庫: {new_storage_status['used']}/{new_storage_status['total']}")
                        storage_status = new_storage_status
                        
                        # 如果倉庫為空，操作成功完成
                        if storage_status['used'] == 0:
                            logger.info("所有物品已從倉庫取出")
                            return True
                    else:
                        logger.warning(f"嘗試 {attempt + 1}: 倉庫狀態未變化")
                        
                except Exception as e:
                    logger.error(f"嘗試 {attempt + 1} 點擊取出按鈕失敗: {e}")
                    await asyncio.sleep(1)
                    continue
            
            # 檢查最終狀態
            final_storage_status = await self.get_storage_status()
            if final_storage_status['used'] == 0:
                logger.info("所有物品已成功從倉庫取出")
                return True
            else:
                logger.error(f"未能取出所有物品，倉庫仍有 {final_storage_status['used']} 個物品")
                return False
                
        except Exception as e:
            logger.error(f"從倉庫取出物品失敗: {e}")
            return False
    
    async def get_inventory_items(self) -> List[InventoryItem]:
        """Get list of items currently in inventory with full details."""
        try:
            if not await self._ensure_on_inventory_accessible_page():
                return []
            
            # Extract inventory items
            items = await self._extract_inventory_items()
            logger.debug(f"獲取到 {len(items)} 件庫存物品")
            return items
            
        except Exception as e:
            logger.error(f"獲取庫存物品列表時出錯: {e}")
            return []
    
    async def calculate_space_requirements(self, market_items: List[Dict[str, Any]]) -> int:
        """Calculate space needed for market items."""
        # For now, assume each market item takes 1 inventory slot
        # This could be enhanced to consider item stacking rules
        total_quantity = sum(item.get('quantity', 1) for item in market_items)
        logger.debug(f"計算空間需求: {len(market_items)} 種物品，總數量 {total_quantity}")
        return total_quantity
    
    async def has_sufficient_space(self, required_space: int) -> bool:
        """Check if there's sufficient space in inventory."""
        status = await self.get_inventory_status()
        if status:
            used = status.get('used', 0)
            total = status.get('total', 0)
            available_space = total - used
            logger.debug(f"檢查空間: 需要 {required_space}，可用 {available_space}")
            return available_space >= required_space
        return False
    
    async def get_selling_slots_status(self) -> Optional[SellingSlotsStatus]:
        """Get current selling slots status (e.g., 2/26)."""
        try:
            # Navigate to marketplace to see selling section
            if not await self.page_navigator.navigate_to_marketplace():
                return None
            
            # 點擊selling標籤來查看銷售狀態
            try:
                selling_button = await self.page.query_selector('button[name="selling"], button:has-text("selling")')
                if selling_button:
                    await selling_button.click()
                    await self.page.wait_for_timeout(1000)  # 等待頁面更新
            except Exception as e:
                logger.debug(f"點擊selling標籤失敗，可能已經在selling頁面: {e}")
            
            # Look for selling section and slot information
            selling_info = await self._extract_selling_slots_info()
            if selling_info:
                status = SellingSlotsStatus(
                    current_listings=selling_info['current'],
                    max_slots=selling_info['max'],
                    listed_items=selling_info.get('items', [])
                )
                logger.debug(f"獲取銷售位狀態: {status.current_listings}/{status.max_slots}")
                return status
                
            logger.warning("無法獲取銷售位狀態信息")
            return None
            
        except Exception as e:
            logger.error(f"獲取銷售位狀態時出錯: {e}")
            return None
    
    async def optimize_inventory_space(self) -> bool:
        """Optimize inventory space by depositing items to storage."""
        logger.info("🎯 開始優化庫存空間...")
        
        try:
            # Check current inventory status
            inventory_status = await self.get_inventory_status()
            if not inventory_status:
                logger.error("❌ 無法獲取庫存狀態")
                return False
            
            # If inventory is not full, no optimization needed
            used = inventory_status.get('used', 0)
            total = inventory_status.get('total', 0)
            is_full = used >= total
            
            if not is_full:
                logger.info(f"ℹ️ 庫存未滿 ({used}/{total})，無需優化")
                return True
            
            # Check storage status
            storage_status = await self.get_storage_status()
            if not storage_status:
                logger.error("❌ 無法獲取倉庫狀態")
                return False
            
            # If storage is also full, cannot optimize
            storage_used = storage_status.get('used', 0)
            storage_total = storage_status.get('total', 0)
            storage_is_full = storage_used >= storage_total
            
            if storage_is_full:
                logger.warning("⚠️ 倉庫也已滿，無法優化庫存空間")
                return False
            
            # Deposit all inventory to storage
            logger.info("📦 庫存已滿，將所有物品存入倉庫...")
            return await self.deposit_all_to_storage()
            
        except Exception as e:
            logger.error(f"❌ 優化庫存空間時出錯: {e}")
            return False
    
    # Private helper methods
    
    async def _ensure_on_inventory_accessible_page(self) -> bool:
        """Ensure we are on a page where inventory is accessible."""
        if self.page is None:
            logger.error("瀏覽器頁面未初始化")
            return False
        
        current_url = self.page.url
        # Inventory is accessible on marketplace and storage pages
        if "page=35" in current_url or "page=50" in current_url:
            return True
        
        logger.info("不在可訪問庫存的頁面，導航到市場頁面...")
        return await self.page_navigator.navigate_to_marketplace()
    
    async def _extract_inventory_info(self) -> Optional[Dict[str, Any]]:
        """Extract inventory information from current page using actual DOM structure."""
        try:
            # 使用實際的HTML結構 - 庫存使用table結構
            inventory_slots = await self.page.query_selector_all("#inventory td.validSlot")
            if not inventory_slots:
                logger.warning("無法找到庫存槽位元素")
                return {'current': 0, 'max': 26, 'items': []}
            
            total_slots = len(inventory_slots)  # 總共26個槽位
            used_slots = 0
            items = []
            
            for i, slot in enumerate(inventory_slots, 1):
                # 檢查槽位中是否有物品
                item_element = await slot.query_selector('.item')
                if item_element:
                    used_slots += 1
                    
                    # 提取物品詳細信息
                    item_info = await self._parse_item_element(item_element, i)
                    if item_info:
                        items.append(item_info)
            
            logger.debug(f"庫存分析: {used_slots}/{total_slots} 槽位已使用，找到 {len(items)} 個物品")
            
            return {
                'current': used_slots,
                'max': total_slots,
                'items': items
            }
            
        except Exception as e:
            logger.error(f"提取庫存信息時出錯: {e}")
            return {'current': 0, 'max': 26, 'items': []}
    
    async def _extract_storage_info(self) -> Optional[Dict[str, Any]]:
        """Extract storage information from current page using actual DOM structure."""
        try:
            # 使用實際的HTML結構 - 倉庫使用div結構
            storage_slots = await self.page.query_selector_all("#storage #normalContainer .slot.validSlot")
            if not storage_slots:
                logger.warning("無法找到倉庫槽位元素")
                return {'current': 0, 'max': 40, 'items': []}
            
            total_slots = len(storage_slots)  # 總共40個槽位
            used_slots = 0
            items = []
            
            for slot in storage_slots:
                # 獲取槽位編號
                slot_number = await slot.get_attribute('data-slot')
                slot_num = int(slot_number) if slot_number else 0
                
                # 檢查槽位中是否有物品
                item_element = await slot.query_selector('.item')
                if item_element:
                    used_slots += 1
                    
                    # 提取物品詳細信息
                    item_info = await self._parse_item_element(item_element, slot_num)
                    if item_info:
                        items.append(item_info)
            
            logger.debug(f"倉庫分析: {used_slots}/{total_slots} 槽位已使用，找到 {len(items)} 個物品")
            
            return {
                'current': used_slots,
                'max': total_slots,
                'items': items
            }
            
        except Exception as e:
            logger.error(f"提取倉庫信息時出錯: {e}")
            return {'current': 0, 'max': 40, 'items': []}
    
    async def _parse_item_element(self, item_element, slot_number: int) -> Optional[InventoryItem]:
        """Parse item element to extract detailed item information."""
        try:
            # 提取物品屬性
            item_type = await item_element.get_attribute('data-type') or 'unknown'
            quantity_str = await item_element.get_attribute('data-quantity')
            quality_str = await item_element.get_attribute('data-quality')
            item_category = await item_element.get_attribute('data-itemtype') or 'item'
            
            # 處理數量（子彈等有數量，其他物品默認為1）
            quantity = int(quantity_str) if quantity_str else 1
            quality = int(quality_str) if quality_str else 1
            
            # 使用配置映射獲取物品名稱
            from ..config.trading_config import config_manager
            item_name = config_manager.get_item_name_by_id(item_type)
            
            # 如果配置映射中沒有找到，使用舊的映射或默認名稱
            if not item_name:
                item_name = self.item_type_mapping.get(item_type, item_type.replace('_', ' ').title())
            
            item_info = InventoryItem(
                slot=slot_number,
                item_type=item_type,
                item_name=item_name,
                quantity=quantity,
                quality=quality,
                item_category=item_category
            )
            
            logger.debug(f"解析物品: 槽位{slot_number} - {item_info}")
            return item_info
            
        except Exception as e:
            logger.error(f"解析物品元素時出錯: {e}")
            return None
    
    async def _extract_selling_slots_info(self) -> Optional[Dict[str, Any]]:
        """Extract selling slots information from marketplace page."""
        try:
            # Look for selling section
            page_text = await self.page.inner_text("body")
            
            # 更精確的銷售位模式匹配
            selling_patterns = [
                r'(\d+)\s*/\s*(\d+)(?=\s*(?:\*|$|\n))',  # "2 / 26" 後面可能跟著 * 或結束
                r'(\d+)/(\d+)\s*(?:slots?|位|個)',       # "2/26 slots" 格式
                r'Selling:\s*(\d+)/(\d+)',               # "Selling: 2/26" 格式
                r'Listed:\s*(\d+)/(\d+)',                # "Listed: 2/26" 格式
                r'銷售:\s*(\d+)/(\d+)',                  # 中文格式
            ]
            
            for pattern in selling_patterns:
                matches = re.finditer(pattern, page_text, re.IGNORECASE)
                for match in matches:
                    current = int(match.group(1))
                    max_slots = int(match.group(2))
                    
                    # 驗證數值合理性（銷售位通常不會超過50）
                    if max_slots <= 50 and current <= max_slots:
                        logger.debug(f"從模式 '{pattern}' 找到銷售位信息: {current}/{max_slots}")
                        return {
                            'current': current,
                            'max': max_slots,
                            'items': []  # Could be enhanced to get actual listed items
                        }
            
            # 如果沒有找到，返回默認值
            logger.warning("無法從頁面文本中找到銷售位信息，使用默認值")
            return {
                'current': 0,
                'max': 26,  # 根據用戶提供的信息，銷售位最大數量是26
                'items': []
            }
            
        except Exception as e:
            logger.error(f"提取銷售位信息時出錯: {e}")
            return None
    
    async def _extract_inventory_items(self) -> List[InventoryItem]:
        """Extract list of items in inventory with full details."""
        try:
            inventory_info = await self._extract_inventory_info()
            if inventory_info and inventory_info.get('items'):
                return inventory_info['items']
            return []
            
        except Exception as e:
            logger.error(f"提取庫存物品時出錯: {e}")
            return []
    
    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid."""
        if self._cache_timestamp is None:
            return False
        
        age = (datetime.now() - self._cache_timestamp).total_seconds()
        return age < self._cache_duration
    
    def _update_inventory_cache(self, status: Dict[str, Any]) -> None:
        """Update inventory cache."""
        self._inventory_cache = status
        self._cache_timestamp = datetime.now()

    def _update_storage_cache(self, status: Dict[str, Any]) -> None:
        """Update storage cache."""
        self._storage_cache = status
        self._cache_timestamp = datetime.now()
    
    def _clear_cache(self) -> None:
        """Clear all cache."""
        self._inventory_cache = None
        self._storage_cache = None
        self._cache_timestamp = None 