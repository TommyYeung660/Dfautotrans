"""
Dead Frontier 自動交易系統 - 銷售策略模組

這個模組負責管理庫存物品的銷售策略和定價決策。
"""

import asyncio
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta

from ..data.models import (
    InventoryItemData, SellOrder, TradingConfiguration, 
    SystemResources, SellingSlotsStatus
)

logger = logging.getLogger(__name__)


class SellingStrategy:
    """智能銷售策略引擎"""
    
    def __init__(self, config: TradingConfiguration):
        """
        初始化銷售策略
        
        Args:
            config: 交易配置參數
        """
        self.config = config
        self.sell_history: List[SellOrder] = []  # 銷售歷史
        self.price_history: Dict[str, List[float]] = {}  # 物品價格歷史
        
        # 物品銷售優先級設定
        self.selling_priorities = {
            "ammo": 0.8,      # 彈藥 - 高優先級
            "medical": 0.9,   # 醫療用品 - 最高優先級
            "weapon": 0.6,    # 武器 - 中等優先級
            "armor": 0.5,     # 護甲 - 中等優先級
            "food": 0.7,      # 食物 - 較高優先級
            "misc": 0.4,      # 雜項 - 低優先級
        }
        
        # 熱門物品的建議定價
        self.popular_item_pricing = {
            "12.7mm Rifle Bullets": {"base_price": 15.0, "markup": 1.15},
            "7.62mm Rifle Bullets": {"base_price": 12.0, "markup": 1.15},
            "5.56mm Rifle Bullets": {"base_price": 10.0, "markup": 1.15},
            "12 Gauge Shells": {"base_price": 8.0, "markup": 1.20},
            "Pain Killers": {"base_price": 25.0, "markup": 1.30},
            "Bandages": {"base_price": 15.0, "markup": 1.25},
        }
        
        logger.info("銷售策略初始化完成")

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
                sell_order = await self._evaluate_selling_item(item, resources)
                if sell_order:
                    sell_orders.append(sell_order)
            except Exception as e:
                logger.warning(f"評估銷售物品時出錯 {item.item_name}: {e}")
                continue
        
        # 按優先級排序
        sell_orders.sort(key=lambda x: x.priority_score, reverse=True)
        
        # 限制銷售數量到可用銷售位
        available_slots = selling_slots_status.available_slots
        selected_orders = sell_orders[:available_slots]
        
        # 優化銷售位分配
        optimized_orders = self._optimize_selling_slots(selected_orders, available_slots)
        
        logger.info(f"銷售策略制定完成，計劃銷售 {len(optimized_orders)} 個物品")
        return optimized_orders

    async def _evaluate_selling_item(
        self, 
        item: InventoryItemData, 
        resources: SystemResources
    ) -> Optional[SellOrder]:
        """評估單個物品的銷售價值"""
        
        try:
            # 計算銷售價格
            selling_price = self._calculate_selling_price(item)
            if selling_price <= 0:
                return None
            
            # 計算優先級評分
            priority_score = self._calculate_selling_priority(item, selling_price)
            
            return SellOrder(
                item=item,
                selling_price=selling_price,
                priority_score=priority_score
            )
            
        except Exception as e:
            logger.warning(f"評估銷售物品失敗 {item.item_name}: {e}")
            return None

    def _calculate_selling_price(self, item: InventoryItemData) -> float:
        """計算物品的銷售價格"""
        
        # 基於熱門物品的定價
        if item.item_name in self.popular_item_pricing:
            pricing_info = self.popular_item_pricing[item.item_name]
            base_price = pricing_info["base_price"]
            markup = pricing_info["markup"]
            return base_price * markup
        
        # 基於歷史價格的定價
        if item.item_name in self.price_history:
            history = self.price_history[item.item_name]
            if len(history) >= 3:
                # 使用最近價格的平均值加上小幅加價
                recent_avg = sum(history[-5:]) / len(history[-5:])
                return recent_avg * 1.10  # 10%加價
        
        # 基於物品類型的通用定價
        category = self._categorize_item(item.item_name)
        base_multipliers = {
            "ammo": 1.15,     # 彈藥15%利潤
            "weapon": 1.25,   # 武器25%利潤
            "armor": 1.20,    # 護甲20%利潤
            "medical": 1.30,  # 醫療用品30%利潤
            "food": 1.20,     # 食物20%利潤
            "misc": 1.40,     # 雜項40%利潤
        }
        
        # 如果有購買價格記錄，基於購買價格定價
        if hasattr(item, 'purchase_price') and item.purchase_price > 0:
            multiplier = base_multipliers.get(category, 1.25)
            return item.purchase_price * multiplier
        
        # 使用市場估價（基於物品類型的基準價格）
        base_prices = {
            "12.7mm Rifle Bullets": 15.0,
            "7.62mm Rifle Bullets": 12.0,
            "5.56mm Rifle Bullets": 10.0,
            "12 Gauge Shells": 8.0,
            "Pain Killers": 25.0,
            "Bandages": 15.0,
        }
        
        if item.item_name in base_prices:
            return base_prices[item.item_name] * 1.15
        
        # 默認定價策略
        return 1000.0  # 默認最低價格

    def _calculate_selling_priority(self, item: InventoryItemData, selling_price: float) -> float:
        """計算物品的銷售優先級評分"""
        
        # 基礎評分基於銷售價格
        base_score = selling_price / 100.0
        
        # 物品類型優先級調整
        category = self._categorize_item(item.item_name)
        category_multiplier = self.selling_priorities.get(category, 0.5)
        score = base_score * category_multiplier
        
        # 熱門物品加分
        if item.item_name in self.popular_item_pricing:
            score *= 1.3
        
        # 數量調整（數量越多，優先級越高）
        if hasattr(item, 'quantity') and item.quantity > 1:
            if item.quantity >= 1000:
                score *= 1.2  # 大量物品優先銷售
            elif item.quantity >= 500:
                score *= 1.1
        
        # 庫存時間調整（如果有的話）
        if hasattr(item, 'acquired_date'):
            days_in_inventory = (datetime.now() - item.acquired_date).days
            if days_in_inventory > 7:
                score *= 1.5  # 庫存時間長的物品優先銷售
            elif days_in_inventory > 3:
                score *= 1.2
        
        return score

    def _categorize_item(self, item_name: str) -> str:
        """根據物品名稱分類"""
        
        name_lower = item_name.lower()
        
        if any(keyword in name_lower for keyword in ["bullet", "shell", "ammo", "round"]):
            return "ammo"
        elif any(keyword in name_lower for keyword in ["rifle", "pistol", "shotgun", "weapon"]):
            return "weapon"
        elif any(keyword in name_lower for keyword in ["armor", "vest", "helmet", "protection"]):
            return "armor"
        elif any(keyword in name_lower for keyword in ["painkiller", "bandage", "medical", "health"]):
            return "medical"
        elif any(keyword in name_lower for keyword in ["food", "water", "drink", "meal"]):
            return "food"
        else:
            return "misc"

    def _optimize_selling_slots(
        self, 
        sell_orders: List[SellOrder], 
        available_slots: int
    ) -> List[SellOrder]:
        """優化銷售位分配"""
        
        if len(sell_orders) <= available_slots:
            # 分配銷售位編號
            for i, order in enumerate(sell_orders):
                order.slot_position = i + 1
            return sell_orders
        
        # 如果物品數量超過可用銷售位，進行優化選擇
        
        # 優先選擇高價值、高優先級的物品
        optimized_orders = []
        total_value = 0.0
        
        for order in sell_orders:
            if len(optimized_orders) >= available_slots:
                break
            
            # 檢查是否值得占用一個銷售位
            expected_value = order.selling_price * order.item.quantity
            if expected_value >= 1000:  # 最低價值門檻
                optimized_orders.append(order)
                total_value += expected_value
        
        # 分配銷售位編號
        for i, order in enumerate(optimized_orders):
            order.slot_position = i + 1
        
        logger.info(f"銷售位優化完成，預期總價值: ${total_value:,.0f}")
        return optimized_orders

    def update_price_history(self, item_name: str, price: float):
        """更新物品價格歷史"""
        if item_name not in self.price_history:
            self.price_history[item_name] = []
        
        self.price_history[item_name].append(price)
        
        # 只保留最近20個價格記錄
        if len(self.price_history[item_name]) > 20:
            self.price_history[item_name] = self.price_history[item_name][-20:]

    def record_sale(self, sell_order: SellOrder):
        """記錄銷售操作"""
        self.sell_history.append(sell_order)
        
        # 只保留最近100個銷售記錄
        if len(self.sell_history) > 100:
            self.sell_history = self.sell_history[-100:]
        
        # 更新價格歷史
        self.update_price_history(
            sell_order.item.item_name,
            sell_order.selling_price
        )
        
        logger.info(f"記錄銷售: {sell_order.item.item_name} - 價格: ${sell_order.selling_price}")

    def get_recommended_pricing(self, item_name: str) -> Optional[float]:
        """獲取物品的建議定價"""
        
        # 熱門物品定價
        if item_name in self.popular_item_pricing:
            pricing_info = self.popular_item_pricing[item_name]
            return pricing_info["base_price"] * pricing_info["markup"]
        
        # 歷史價格定價
        if item_name in self.price_history and len(self.price_history[item_name]) >= 3:
            recent_prices = self.price_history[item_name][-5:]
            return sum(recent_prices) / len(recent_prices) * 1.05  # 5%加價
        
        return None

    def analyze_selling_performance(self) -> Dict[str, any]:
        """分析銷售性能"""
        
        if not self.sell_history:
            return {"total_sales": 0}
        
        recent_sales = self.sell_history[-20:]  # 最近20次銷售
        
        total_value = sum(
            order.selling_price * order.item.quantity 
            for order in recent_sales
        )
        
        category_performance = {}
        for order in recent_sales:
            category = self._categorize_item(order.item.item_name)
            if category not in category_performance:
                category_performance[category] = {"count": 0, "total_value": 0.0}
            
            category_performance[category]["count"] += 1
            category_performance[category]["total_value"] += order.selling_price * order.item.quantity
        
        return {
            "total_sales": len(self.sell_history),
            "recent_total_value": total_value,
            "recent_average_value": total_value / len(recent_sales) if recent_sales else 0,
            "category_performance": category_performance,
            "popular_items_sold": len([
                order for order in recent_sales 
                if order.item.item_name in self.popular_item_pricing
            ])
        }

    def should_clear_inventory_space(
        self, 
        inventory_items: List[InventoryItemData],
        space_needed: int
    ) -> List[SellOrder]:
        """
        決定是否需要清理庫存空間
        
        Args:
            inventory_items: 當前庫存物品
            space_needed: 需要的空間數量
            
        Returns:
            建議銷售的物品訂單列表
        """
        
        if space_needed <= 0:
            return []
        
        logger.info(f"需要清理庫存空間: {space_needed} 個位置")
        
        # 選擇優先級最低的物品進行銷售
        sell_candidates = []
        
        for item in inventory_items:
            try:
                selling_price = self._calculate_selling_price(item)
                priority_score = self._calculate_selling_priority(item, selling_price)
                
                # 為了清理空間，降低優先級評分
                priority_score *= 0.5
                
                sell_order = SellOrder(
                    item=item,
                    selling_price=selling_price,
                    priority_score=priority_score
                )
                sell_candidates.append(sell_order)
                
            except Exception as e:
                logger.warning(f"評估清理物品時出錯 {item.item_name}: {e}")
                continue
        
        # 按優先級排序（優先級低的先銷售）
        sell_candidates.sort(key=lambda x: x.priority_score)
        
        # 選擇需要的數量
        space_clearing_orders = sell_candidates[:space_needed]
        
        logger.info(f"建議銷售 {len(space_clearing_orders)} 個物品以清理空間")
        return space_clearing_orders 