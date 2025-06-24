"""Inventory management module for Dead Frontier Auto Trading System."""

import asyncio
import re
from typing import Optional, List, Dict, Any
from datetime import datetime
from loguru import logger

from ..config.settings import Settings
from ..automation.browser_manager import BrowserManager
from ..core.page_navigator import PageNavigator
from ..data.models import InventoryStatus, StorageStatus, SellingSlotsStatus


class InventoryManager:
    """Handles all inventory and storage management operations."""
    
    def __init__(self, settings: Settings, browser_manager: BrowserManager, page_navigator: PageNavigator):
        self.settings = settings
        self.browser_manager = browser_manager
        self.page_navigator = page_navigator
        self.page = browser_manager.page
        
        # Cache for inventory information
        self._inventory_cache: Optional[InventoryStatus] = None
        self._storage_cache: Optional[StorageStatus] = None
        self._cache_timestamp: Optional[datetime] = None
        self._cache_duration = 30  # seconds
        
    async def get_inventory_status(self) -> Dict[str, Any]:
        """Get current inventory status."""
        try:
            # Navigate to storage page to access inventory info
            if not await self.page_navigator.navigate_to_storage():
                return {'used': 0, 'total': 0, 'items': []}
                
            # Look for inventory information patterns
            inventory_info = await self._extract_inventory_info()
            if inventory_info:
                return {
                    'used': inventory_info['current'],
                    'total': inventory_info['max'],
                    'items': inventory_info.get('items', [])
                }
                
            logger.warning("無法獲取庫存狀態信息")
            return {'used': 0, 'total': 0, 'items': []}
            
        except Exception as e:
            logger.error(f"獲取庫存狀態時出錯: {e}")
            return {'used': 0, 'total': 0, 'items': []}
    
    async def get_storage_status(self) -> Dict[str, Any]:
        """Get current storage status."""
        try:
            # Navigate to storage page
            if not await self.page_navigator.navigate_to_storage():
                return {'used': 0, 'total': 0, 'items': []}
                
            # Look for storage information patterns
            storage_info = await self._extract_storage_info()
            if storage_info:
                return {
                    'used': storage_info['current'],
                    'total': storage_info['max'],
                    'items': storage_info.get('items', [])
                }
                
            logger.warning("無法獲取倉庫狀態信息")
            return {'used': 0, 'total': 0, 'items': []}
            
        except Exception as e:
            logger.error(f"獲取倉庫狀態時出錯: {e}")
            return {'used': 0, 'total': 0, 'items': []}
    
    async def check_inventory_full(self) -> bool:
        """Check if inventory is full."""
        status = await self.get_inventory_status()
        if status:
            return status.is_full
        return False
    
    async def deposit_all_to_storage(self) -> bool:
        """Deposit all inventory items to storage."""
        logger.info("📦 準備將所有庫存物品存入倉庫...")
        
        try:
            # Navigate to storage page
            if not await self.page_navigator.navigate_to_storage():
                logger.error("❌ 無法導航到倉庫頁面")
                return False
            
            # Look for "deposit all" button - 使用正確的按鈕ID
            deposit_all_selectors = [
                "#invtostorage",  # 從Inventory全部存入到Storage的正確按鈕ID
                "button:text('deposit all')",
                "input[value='deposit all']",
                "button:text('Deposit All')",
                "input[value='Deposit All']",
                "button:has-text('deposit all')",
                ".deposit-all-button",
                "#depositAllButton",
                "button[onclick*='depositall']",
                "button[onclick*='deposit_all']"
            ]
            
            deposit_button = None
            for selector in deposit_all_selectors:
                try:
                    deposit_button = await self.page.query_selector(selector)
                    if deposit_button:
                        # 檢查按鈕是否被禁用
                        is_disabled = await deposit_button.is_disabled()
                        if is_disabled:
                            logger.warning(f"找到存入按鈕 {selector} 但已被禁用")
                            continue
                        logger.debug(f"找到可用的存入所有物品按鈕: {selector}")
                        break
                except Exception:
                    continue
            
            if not deposit_button:
                # 檢查是否是因為庫存為空導致按鈕被禁用
                inventory_status = await self.get_inventory_status()
                if inventory_status and inventory_status.current_count == 0:
                    logger.info("ℹ️ 庫存為空，無需存入操作")
                    return True
                else:
                    logger.error("❌ 找不到可用的存入所有物品按鈕")
                    return False
            
            # Get inventory status before deposit
            initial_inventory = await self.get_inventory_status()
            
            # Click deposit all button
            await deposit_button.click()
            logger.info("✅ 已點擊存入所有物品按鈕")
            
            # Wait for operation to complete
            await asyncio.sleep(3)
            
            # Clear cache to get fresh data
            self._clear_cache()
            
            # Verify operation success
            new_inventory = await self.get_inventory_status()
            
            if new_inventory and initial_inventory:
                if new_inventory.current_count < initial_inventory.current_count:
                    deposited_count = initial_inventory.current_count - new_inventory.current_count
                    logger.info(f"✅ 成功存入 {deposited_count} 件物品到倉庫")
                    return True
                elif new_inventory.current_count == 0:
                    logger.info(f"✅ 成功存入所有 {initial_inventory.current_count} 件物品到倉庫")
                    return True
                else:
                    logger.warning("⚠️ 存入操作可能未完全成功")
                    return False
            else:
                logger.warning("⚠️ 無法驗證存入操作結果")
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
    
    async def get_inventory_items(self) -> List[str]:
        """Get list of items currently in inventory."""
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
            available_space = status.available_space
            logger.debug(f"檢查空間: 需要 {required_space}，可用 {available_space}")
            return available_space >= required_space
        return False
    
    async def get_selling_slots_status(self) -> Optional[SellingSlotsStatus]:
        """Get current selling slots status (e.g., 6/30)."""
        try:
            # Navigate to marketplace to see selling section
            if not await self.page_navigator.navigate_to_marketplace():
                return None
            
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
            if not inventory_status.is_full:
                logger.info(f"ℹ️ 庫存未滿 ({inventory_status.current_count}/{inventory_status.max_capacity})，無需優化")
                return True
            
            # Check storage status
            storage_status = await self.get_storage_status()
            if not storage_status:
                logger.error("❌ 無法獲取倉庫狀態")
                return False
            
            # If storage is also full, cannot optimize
            if storage_status.is_full:
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
            # 計算庫存使用情況 - 基於實際的HTML結構
            # 查找所有庫存槽位
            inventory_slots = await self.page.query_selector_all("#inventoryholder .validSlot")
            total_slots = len(inventory_slots)
            
            # 計算已使用的槽位（包含.item的槽位）
            used_slots = 0
            items = []
            
            for slot in inventory_slots:
                item_element = await slot.query_selector(".item")
                if item_element:
                    used_slots += 1
                    # 獲取物品信息
                    item_type = await item_element.get_attribute("data-type")
                    if item_type:
                        items.append(item_type)
            
            logger.debug(f"庫存狀態分析: {used_slots}/{total_slots} 槽位已使用")
            
            # 如果找不到庫存槽位，嘗試從頁面文本中解析
            if total_slots == 0:
                page_text = await self.page.inner_text("body")
                
                # Pattern to match "Items: X/Y" or similar
                inventory_patterns = [
                    r'Items:\s*(\d+)/(\d+)',
                    r'Inventory:\s*(\d+)/(\d+)',
                    r'庫存:\s*(\d+)/(\d+)',
                    r'物品:\s*(\d+)/(\d+)'
                ]
                
                for pattern in inventory_patterns:
                    match = re.search(pattern, page_text, re.IGNORECASE)
                    if match:
                        current = int(match.group(1))
                        max_capacity = int(match.group(2))
                        logger.debug(f"從模式 '{pattern}' 找到庫存信息: {current}/{max_capacity}")
                        return {
                            'current': current,
                            'max': max_capacity,
                            'items': []
                        }
                
                # 默認值
                return {
                    'current': 0,
                    'max': 50,  # Default capacity
                    'items': []
                }
            
            return {
                'current': used_slots,
                'max': total_slots,
                'items': items
            }
            
        except Exception as e:
            logger.error(f"提取庫存信息時出錯: {e}")
            return None
    
    async def _extract_storage_info(self) -> Optional[Dict[str, Any]]:
        """Extract storage information from current page using actual DOM structure."""
        try:
            # 計算倉庫使用情況 - 基於實際的HTML結構
            # 查找所有有效槽位
            all_slots = await self.page.query_selector_all("#normalContainer .validSlot")
            total_slots = len(all_slots)
            
            # 計算已使用的槽位（包含.item的槽位）
            used_slots = 0
            items = []
            
            for slot in all_slots:
                item_element = await slot.query_selector(".item")
                if item_element:
                    used_slots += 1
                    # 獲取物品信息
                    item_type = await item_element.get_attribute("data-type")
                    if item_type:
                        items.append(item_type)
            
            logger.debug(f"倉庫狀態分析: {used_slots}/{total_slots} 槽位已使用")
            
            return {
                'current': used_slots,
                'max': total_slots,
                'items': items
            }
            
        except Exception as e:
            logger.error(f"提取倉庫信息時出錯: {e}")
            # 如果無法獲取實際信息，返回默認值
            return {
                'current': 0,
                'max': 1000,  # Default capacity
                'items': []
            }
    
    async def _extract_selling_slots_info(self) -> Optional[Dict[str, Any]]:
        """Extract selling slots information from marketplace page."""
        try:
            # Look for selling section
            page_text = await self.page.inner_text("body")
            
            # Pattern to match selling slots like "6/30"
            selling_patterns = [
                r'(\d+)/(\d+)\s*(?:slots?|位|個)',
                r'Selling:\s*(\d+)/(\d+)',
                r'Listed:\s*(\d+)/(\d+)',
                r'銷售:\s*(\d+)/(\d+)'
            ]
            
            for pattern in selling_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    current = int(match.group(1))
                    max_slots = int(match.group(2))
                    logger.debug(f"從模式 '{pattern}' 找到銷售位信息: {current}/{max_slots}")
                    return {
                        'current': current,
                        'max': max_slots,
                        'items': []  # Could be enhanced to get actual listed items
                    }
            
            # Default selling slots info
            return {
                'current': 0,
                'max': 30,  # Default max slots
                'items': []
            }
            
        except Exception as e:
            logger.error(f"提取銷售位信息時出錯: {e}")
            return None
    
    async def _extract_inventory_items(self) -> List[str]:
        """Extract list of items in inventory."""
        try:
            # Look for inventory item elements
            inventory_selectors = [
                ".inventory-item",
                ".item",
                "[class*='inventory'] .item",
                "[id*='inventory'] .item"
            ]
            
            items = []
            for selector in inventory_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    for element in elements:
                        item_text = await element.inner_text()
                        if item_text and item_text.strip():
                            items.append(item_text.strip())
                    
                    if items:
                        logger.debug(f"從選擇器 '{selector}' 找到 {len(items)} 件物品")
                        break
                except Exception:
                    continue
            
            return items
            
        except Exception as e:
            logger.error(f"提取庫存物品時出錯: {e}")
            return []
    
    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid."""
        if self._cache_timestamp is None:
            return False
        
        age = (datetime.now() - self._cache_timestamp).total_seconds()
        return age < self._cache_duration
    
    def _update_inventory_cache(self, status: InventoryStatus) -> None:
        """Update inventory cache."""
        self._inventory_cache = status
        self._cache_timestamp = datetime.now()
    
    def _update_storage_cache(self, status: StorageStatus) -> None:
        """Update storage cache."""
        self._storage_cache = status
        self._cache_timestamp = datetime.now()
    
    def _clear_cache(self) -> None:
        """Clear all cache."""
        self._inventory_cache = None
        self._storage_cache = None
        self._cache_timestamp = None 