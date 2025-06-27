"""
Dead Frontier 自動交易系統 - 銷售策略模組

簡化的銷售策略，基於 trading_config.json 配置進行定價。
"""

import asyncio
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import pytz

from ..data.models import (
    InventoryItemData, SellOrder, TradingConfiguration, 
    SystemResources, SellingSlotsStatus
)
from ..config.trading_config import TradingConfig

logger = logging.getLogger(__name__)


class SellingStrategy:
    """簡化的銷售策略引擎，基於配置定價"""
    
    def __init__(self, config: TradingConfiguration, trading_config: Optional[TradingConfig] = None):
        """
        初始化銷售策略
        
        Args:
            config: 交易配置參數（向後兼容）
            trading_config: 新的交易配置（可選）
        """
        self.legacy_config = config
        
        # 使用新的配置系統
        if trading_config:
            self.trading_config = trading_config
        else:
            from ..config.trading_config import TradingConfigManager
            config_manager = TradingConfigManager()
            self.trading_config = config_manager.load_config()
        
        # 向後兼容的配置屬性
        self.config = config
        self.sell_history: List[SellOrder] = []  # 銷售歷史
        
        logger.info("銷售策略初始化完成")
        
    def _is_us_peak_hours(self) -> bool:
        """檢查當前是否為美國高峰時段（美國東部時間19:00-23:59）"""
        if not self.trading_config.selling.peak_hours_enabled:
            return False
            
        try:
            # 獲取美國東部時間
            us_eastern = pytz.timezone('US/Eastern')
            us_time = datetime.now(us_eastern)
            current_hour = us_time.hour
            
            start_hour = self.trading_config.selling.peak_hours_start
            end_hour = self.trading_config.selling.peak_hours_end
            
            # 處理跨日情況
            if start_hour <= end_hour:
                is_peak = start_hour <= current_hour <= end_hour
            else:
                is_peak = current_hour >= start_hour or current_hour <= end_hour
            
            logger.debug(f"美國東部時間: {us_time.strftime('%H:%M')}, 高峰時段: {is_peak}")
            return is_peak
            
        except Exception as e:
            logger.warning(f"檢查高峰時段時出錯: {e}")
            return False

    async def plan_selling_strategy(
        self, 
        inventory_items: List[InventoryItemData],
        selling_slots_status: SellingSlotsStatus,
        resources: SystemResources
    ) -> List[SellOrder]:
        """
        制定銷售策略
        
        Args:
            inventory_items: 庫存物品列表
            selling_slots_status: 銷售位狀態
            resources: 系統資源狀況
            
        Returns:
            排序後的銷售訂單列表
        """
        logger.info(f"開始制定銷售策略，庫存物品: {len(inventory_items)}, 可用銷售位: {selling_slots_status.available_slots}")
        
        if not inventory_items:
            logger.info("沒有庫存物品可供銷售")
            return []
        
        if selling_slots_status.available_slots <= 0:
            logger.info("沒有可用的銷售位")
            return []
        
        sell_orders = []
        
        # 評估每個物品的銷售價值
        for item in inventory_items:
            try:
                sell_order = await self._evaluate_selling_item(item)
                if sell_order:
                    sell_orders.append(sell_order)
            except Exception as e:
                logger.warning(f"評估銷售物品時出錯 {item.item_name}: {e}")
                continue
        
        # 按價格排序（高價優先）
        sell_orders.sort(key=lambda x: x.selling_price * x.item.quantity, reverse=True)
        
        # 限制銷售數量到可用銷售位和配置限制
        available_slots = selling_slots_status.available_slots
        max_selling_slots = self.trading_config.selling.max_selling_slots_used
        selling_threshold = self.trading_config.selling.selling_slots_threshold_percentage
        
        # 計算實際可用的銷售位
        total_selling_slots = selling_slots_status.max_slots
        current_used_slots = selling_slots_status.current_listings
        
        # 根據閾值限制銷售位使用
        max_allowed_slots = int(total_selling_slots * selling_threshold)
        remaining_slots_by_threshold = max_allowed_slots - current_used_slots
        
        # 取最小值作為實際可用銷售位
        actual_available_slots = min(
            available_slots,
            max_selling_slots,
            remaining_slots_by_threshold
        )
        
        logger.debug(f"銷售位計算: 可用{available_slots}, 配置限制{max_selling_slots}, 閾值限制{remaining_slots_by_threshold}, 實際可用{actual_available_slots}")
        
        selected_orders = sell_orders[:actual_available_slots]
        
        # 分配銷售位編號
        for i, order in enumerate(selected_orders):
            order.slot_position = i + 1
        
        logger.info(f"銷售策略制定完成，計劃銷售 {len(selected_orders)} 個物品")
        return selected_orders

    async def _evaluate_selling_item(self, item: InventoryItemData) -> Optional[SellOrder]:
        """評估單個物品的銷售價值"""
        
        try:
            # 計算銷售價格
            selling_price = self._calculate_selling_price(item)
            if selling_price <= 0:
                return None
            
            # 計算總價值作為優先級
            total_value = selling_price * item.quantity
            
            return SellOrder(
                item=item,
                selling_price=selling_price,
                priority_score=total_value
            )
            
        except Exception as e:
            logger.warning(f"評估銷售物品失敗 {item.item_name}: {e}")
            return None

    def _calculate_selling_price(self, item: InventoryItemData) -> float:
        """
        基於 trading_config.json 配置計算物品的銷售價格
        
        邏輯：
        1. 如果物品在配置的 target_items 中，使用對應的 max_price_per_unit 作為買入參考價格
        2. 在買入參考價格基礎上應用 markup_percentage 進行加價以獲得利潤
        3. 如果物品不在配置中，使用默認定價
        """
        
        # 獲取配置中的物品信息
        target_items = self.trading_config.market_search.target_items
        max_buy_prices = self.trading_config.market_search.max_price_per_unit  # 這是買入參考價格
        markup_percentage = self.trading_config.selling.markup_percentage
        
        # 檢查物品是否在配置的目標物品中
        max_buy_price = None
        try:
            item_index = target_items.index(item.item_name)
            max_buy_price = max_buy_prices[item_index]
            logger.debug(f"物品 {item.item_name} 在配置中，買入參考價格: ${max_buy_price}")
        except (ValueError, IndexError):
            logger.debug(f"物品 {item.item_name} 不在配置中，使用默認定價")
        
        if max_buy_price is not None:
            # 正確的定價邏輯：
            # 1. 假設我們以接近 max_buy_price 的價格買入
            # 2. 在此基礎上加價銷售以獲得利潤
            
            # 假設平均買入價格為 max_buy_price 的 85%
            estimated_buy_price = max_buy_price * 0.85
            
            # 獲取加價配置
            markup_percentage = self.trading_config.selling.markup_percentage
            min_markup = self.trading_config.selling.min_markup_percentage
            max_markup = self.trading_config.selling.max_markup_percentage
            
            # 確保加價比例在配置範圍內
            if self.trading_config.selling.price_adjustment_enabled:
                # 可以根據市場情況調整加價比例（這裡簡化為使用配置值）
                actual_markup = max(min_markup, min(markup_percentage, max_markup))
            else:
                # 不啟用價格調整時，使用固定加價比例
                actual_markup = markup_percentage
            
            # 在買入價基礎上加價
            selling_price = estimated_buy_price * (1 + actual_markup)
            
            # 高峰時段價格調整
            if self._is_us_peak_hours():
                peak_multiplier = self.trading_config.selling.peak_hours_selling_multiplier
                original_price = selling_price
                selling_price = selling_price * peak_multiplier
                logger.debug(f"高峰時段銷售價格調整: {item.item_name} ${original_price:.2f} -> ${selling_price:.2f} (+{(peak_multiplier-1)*100:.0f}%)")
            
            # 確保賣出價格合理（不要過高導致無法銷售）
            # 最高不超過 max_buy_price 的 130%（高峰時段放寬到150%）
            max_multiplier = 1.50 if self._is_us_peak_hours() else 1.30
            max_reasonable_price = max_buy_price * max_multiplier
            selling_price = min(selling_price, max_reasonable_price)
            
            logger.debug(f"配置定價: {item.item_name} - 估算買入${estimated_buy_price:.2f}, 加價{actual_markup:.1%} -> 售價${selling_price:.2f} (上限${max_reasonable_price:.2f})")
            return selling_price
        
        # 默認定價策略（對於不在配置中的物品）
        default_prices = {
            "Painkiller": 25.0,
            "Pain Killers": 25.0,
            "Bandage": 15.0,
            "Bandages": 15.0,
            "Cooked Fresh Meat": 8.0,
            "Water": 5.0,
            "Gasoline": 2.5,
        }
        
        # 檢查是否有默認價格
        for item_key, default_price in default_prices.items():
            if item_key.lower() in item.item_name.lower():
                selling_price = default_price * (1 + markup_percentage)
                logger.debug(f"默認定價: {item.item_name} - 基準${default_price} -> 售價${selling_price:.2f}")
                return selling_price
        
        # 最後的備用定價
        fallback_price = 10.0 * (1 + markup_percentage)
        logger.debug(f"備用定價: {item.item_name} -> 售價${fallback_price:.2f}")
        return fallback_price

    def get_recommended_pricing(self, item_name: str) -> Optional[float]:
        """獲取物品的建議定價"""
        
        # 創建一個臨時的 InventoryItemData 對象來計算價格
        temp_item = InventoryItemData(
            item_name=item_name,
            quantity=1,
            location="inventory"
        )
        
        return self._calculate_selling_price(temp_item)

    def record_sale(self, sell_order: SellOrder):
        """記錄銷售操作"""
        self.sell_history.append(sell_order)
        
        # 只保留最近50個銷售記錄
        if len(self.sell_history) > 50:
            self.sell_history = self.sell_history[-50:]
        
        logger.info(f"記錄銷售: {sell_order.item.item_name} - 價格: ${sell_order.selling_price}")

    def analyze_selling_performance(self) -> Dict[str, any]:
        """分析銷售性能"""
        
        if not self.sell_history:
            return {"total_sales": 0, "total_value": 0.0}
        
        recent_sales = self.sell_history[-20:]  # 最近20次銷售
        
        total_value = sum(
            order.selling_price * order.item.quantity 
            for order in recent_sales
        )
        
        return {
            "total_sales": len(self.sell_history),
            "recent_sales": len(recent_sales),
            "recent_total_value": total_value,
            "recent_average_value": total_value / len(recent_sales) if recent_sales else 0,
        }

    def should_clear_inventory_space(
        self, 
        inventory_items: List[InventoryItemData],
        space_needed: int
    ) -> List[SellOrder]:
        """
        決定是否需要清理庫存空間
        使用配置的庫存管理參數
        
        Args:
            inventory_items: 當前庫存物品
            space_needed: 需要的空間數量
            
        Returns:
            建議銷售的物品訂單列表
        """
        
        if space_needed <= 0:
            return []
        
        # 使用配置參數評估庫存壓力
        max_inventory_slots = self.trading_config.selling.max_inventory_slots_used
        inventory_threshold = self.trading_config.selling.inventory_threshold_percentage
        
        current_inventory_count = len(inventory_items)
        inventory_pressure_threshold = int(max_inventory_slots * inventory_threshold)
        
        logger.info(f"庫存空間評估: 當前{current_inventory_count}, 配置上限{max_inventory_slots}, 壓力閾值{inventory_pressure_threshold}, 需要空間{space_needed}")
        
        # 如果庫存壓力不大，只清理必要的空間
        if current_inventory_count < inventory_pressure_threshold:
            space_to_clear = space_needed
            logger.info(f"庫存壓力不大，僅清理必要空間: {space_to_clear}")
        else:
            # 庫存壓力大，積極清理更多空間
            extra_clear = max(5, int(space_needed * 0.5))  # 額外清理50%或至少5個位置
            space_to_clear = space_needed + extra_clear
            logger.info(f"庫存壓力較大，積極清理空間: {space_to_clear} (額外清理{extra_clear})")
        
        # 評估所有物品並按價值排序
        sell_candidates = []
        
        for item in inventory_items:
            try:
                selling_price = self._calculate_selling_price(item)
                total_value = selling_price * item.quantity
                
                sell_order = SellOrder(
                    item=item,
                    selling_price=selling_price,
                    priority_score=total_value
                )
                sell_candidates.append(sell_order)
                
            except Exception as e:
                logger.warning(f"評估清理物品時出錯 {item.item_name}: {e}")
                continue
        
        # 按價值排序（低價值的先銷售）
        sell_candidates.sort(key=lambda x: x.priority_score)
        
        # 選擇需要的數量
        space_clearing_orders = sell_candidates[:space_to_clear]
        
        logger.info(f"建議銷售 {len(space_clearing_orders)} 個物品以清理空間")
        return space_clearing_orders 