"""
Dead Frontier 自動交易系統 - 購買策略模組

簡化的購買策略，基於 trading_config.json 配置進行決策。
"""

import asyncio
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta

from ..data.models import (
    MarketItemData, PurchaseOpportunity, MarketCondition, 
    TradingConfiguration, SystemResources
)
from ..config.trading_config import TradingConfig

logger = logging.getLogger(__name__)


class BuyingStrategy:
    """簡化的購買策略引擎，基於配置決策"""
    
    def __init__(self, config: TradingConfiguration, trading_config: Optional[TradingConfig] = None):
        """
        初始化購買策略
        
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
        self.purchase_history: List[PurchaseOpportunity] = []  # 購買歷史
        
        logger.info(f"購買策略初始化完成，最小利潤率: {config.min_profit_margin:.1%}")

    async def evaluate_market_items(
        self, 
        items: List[MarketItemData], 
        resources: SystemResources
    ) -> List[PurchaseOpportunity]:
        """
        評估市場物品並生成購買機會
        
        Args:
            items: 市場物品列表
            resources: 系統資源狀況
            
        Returns:
            排序後的購買機會列表
        """
        logger.info(f"開始評估 {len(items)} 個市場物品")
        
        opportunities = []
        total_investment = 0.0
        item_type_counts = {}  # 追蹤每種物品類型的購買數量（用於多樣化投資）
        
        for item in items:
            try:
                # 基本過濾條件
                if not self._passes_basic_filters(item, resources):
                    continue
                
                # 多樣化投資檢查
                if self.trading_config.buying.diversification_enabled:
                    item_count = item_type_counts.get(item.item_name, 0)
                    max_same_item = 5  # 每種物品最多買5次，避免過度集中
                    if item_count >= max_same_item:
                        logger.debug(f"跳過 {item.item_name}：已達到多樣化投資限制 ({item_count}/{max_same_item})")
                        continue
                
                # 計算購買機會
                opportunity = await self._evaluate_single_item(item, resources)
                if opportunity:
                    # 檢查投資限制
                    item_cost = item.price * item.quantity
                    if total_investment + item_cost <= resources.total_funds:
                        opportunities.append(opportunity)
                        total_investment += item_cost
                        
                        # 更新物品類型計數
                        if self.trading_config.buying.diversification_enabled:
                            item_type_counts[item.item_name] = item_type_counts.get(item.item_name, 0) + 1
                        
                        logger.debug(f"添加購買機會: {item.item_name} - 利潤率: {opportunity.profit_potential:.1%}")
                    else:
                        logger.debug(f"超出資金限制，跳過: {item.item_name}")
                        
            except Exception as e:
                logger.warning(f"評估物品時出錯 {item.item_name}: {e}")
                continue
        
        # 按利潤率排序（高利潤優先）
        opportunities.sort(key=lambda x: x.profit_potential, reverse=True)
        
        # 限制購買數量
        max_purchases = self.trading_config.buying.max_purchases_per_cycle
        if len(opportunities) > max_purchases:
            opportunities = opportunities[:max_purchases]
        
        logger.info(f"評估完成，找到 {len(opportunities)} 個有價值的購買機會")
        return opportunities

    def _passes_basic_filters(self, item: MarketItemData, resources: SystemResources) -> bool:
        """檢查物品是否通過基本過濾條件"""
        
        # 只考慮配置中的目標物品
        if item.item_name not in self.trading_config.market_search.target_items:
            return False
        
        # 價格過濾 - 使用配置的max_price_per_unit
        max_price = self._get_max_price_for_item(item.item_name)
        if max_price is None or item.price > max_price:
            return False
        
        # 資金檢查
        item_total_price = item.price * item.quantity
        if item_total_price > resources.total_funds:
            return False
        
        # 使用配置的max_items_per_search進行數量合理性檢查
        max_search_items = self.trading_config.market_search.max_items_per_search
        reasonable_max_quantity = max_search_items * 100  # 動態調整合理數量上限
        if item.quantity <= 0 or item.quantity > reasonable_max_quantity:
            return False
        
        return True

    def _get_max_price_for_item(self, item_name: str) -> Optional[float]:
        """獲取物品的最大購買價格"""
        try:
            target_items = self.trading_config.market_search.target_items
            max_prices = self.trading_config.market_search.max_price_per_unit
            
            item_index = target_items.index(item_name)
            return max_prices[item_index]
        except (ValueError, IndexError):
            return None

    async def _evaluate_single_item(
        self, 
        item: MarketItemData, 
        resources: SystemResources
    ) -> Optional[PurchaseOpportunity]:
        """評估單個物品的購買價值"""
        
        try:
            # 估算合理銷售價格
            estimated_sell_price = self._estimate_sell_price(item)
            if estimated_sell_price <= item.price:
                return None
            
            # 計算利潤潛力
            profit_potential = (estimated_sell_price - item.price) / item.price
            if profit_potential < self.trading_config.buying.min_profit_margin:
                return None
            
            # 風險評估 - 使用配置的風險管理參數
            risk_level = self._assess_item_risk(item, profit_potential)
            
            # 計算優先級評分（基於利潤率和物品優先級）
            priority_score = self._calculate_priority_score(item, profit_potential)
            
            return PurchaseOpportunity(
                item=item,
                profit_potential=profit_potential,
                priority_score=priority_score,
                estimated_sell_price=estimated_sell_price,
                risk_level=risk_level
            )
            
        except Exception as e:
            logger.warning(f"評估物品失敗 {item.item_name}: {e}")
            return None

    def _estimate_sell_price(self, item: MarketItemData) -> float:
        """
        基於 trading_config.json 配置估算物品的合理銷售價格
        
        邏輯：使用配置的max_price_per_unit作為買入參考，在此基礎上加價估算售價
        """
        
        # 獲取物品的最大購買價格作為參考
        max_buy_price = self._get_max_price_for_item(item.item_name)
        if max_buy_price is None:
            return item.price * 1.2  # 默認20%利潤
        
        # 使用與 selling_strategy.py 一致的邏輯
        markup_percentage = self.trading_config.selling.markup_percentage
        
        # 假設平均買入價格為 max_buy_price 的 85%
        estimated_buy_price = max_buy_price * 0.85
        
        # 在買入價基礎上加價
        estimated_sell_price = estimated_buy_price * (1 + markup_percentage)
        
        # 確保賣出價格合理（不要過高導致無法銷售）
        # 最高不超過 max_buy_price 的 130%
        max_reasonable_price = max_buy_price * 1.30
        estimated_sell_price = min(estimated_sell_price, max_reasonable_price)
        
        logger.debug(f"估算售價: {item.item_name} - 買入參考${max_buy_price} -> 預估售價${estimated_sell_price:.2f}")
        return estimated_sell_price

    def _calculate_priority_score(self, item: MarketItemData, profit_potential: float) -> float:
        """計算物品的優先級評分"""
        
        # 基礎分數基於利潤率
        score = profit_potential * 100
        
        # 基於配置的優先級調整
        priority_items = self.trading_config.buying.priority_items
        if item.item_name in priority_items:
            priority = priority_items[item.item_name]
            # 優先級越低（數字越小）得分越高
            priority_multiplier = 2.0 - (priority * 0.1)  # 1->1.9, 2->1.8, ..., 7->1.3
            score *= priority_multiplier
        
        # 數量合理性調整
        if 100 <= item.quantity <= 2000:
            score *= 1.1  # 合理數量加分
        elif item.quantity > 5000:
            score *= 0.9  # 數量過大減分
        
        # 價格合理性調整
        item_total_price = item.price * item.quantity
        if 1000 <= item_total_price <= 30000:
            score *= 1.1  # 合理總價加分
        
        return score

    def _assess_item_risk(self, item: MarketItemData, profit_potential: float) -> str:
        """
        基於配置參數評估物品風險等級
        """
        # 基於總價評估風險
        total_price = item.price * item.quantity
        
        # 高價物品風險較高
        if total_price > 30000:
            risk_level = "high"
        elif total_price > 10000:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        # 基於利潤率調整風險
        if profit_potential < self.trading_config.buying.min_profit_margin * 1.2:
            # 利潤率接近最低要求，風險較高
            if risk_level == "low":
                risk_level = "medium"
            elif risk_level == "medium":
                risk_level = "high"
        
        # 基於數量評估風險
        if item.quantity > 2000:
            if risk_level == "low":
                risk_level = "medium"
        
        logger.debug(f"風險評估: {item.item_name} - 總價${total_price}, 利潤率{profit_potential:.1%} -> {risk_level}")
        return risk_level

    def get_market_condition_assessment(
        self, 
        opportunities: List[PurchaseOpportunity]
    ) -> MarketCondition:
        """評估當前市場狀況"""
        
        total_scanned = len(opportunities) * 2  # 估算掃描的總物品數
        valuable_opportunities = len(opportunities)
        
        if valuable_opportunities == 0:
            avg_profit_margin = 0.0
            activity_level = "low"
        else:
            avg_profit_margin = sum(op.profit_potential for op in opportunities) / valuable_opportunities
            
            if valuable_opportunities >= 10:
                activity_level = "high"
            elif valuable_opportunities >= 5:
                activity_level = "medium"
            else:
                activity_level = "low"
        
        return MarketCondition(
            total_items_scanned=total_scanned,
            valuable_opportunities=valuable_opportunities,
            average_profit_margin=avg_profit_margin,
            market_activity_level=activity_level,
            last_scan_time=datetime.now()
        )

    def record_purchase(self, opportunity: PurchaseOpportunity):
        """記錄購買操作"""
        self.purchase_history.append(opportunity)
        
        # 只保留最近50個購買記錄
        if len(self.purchase_history) > 50:
            self.purchase_history = self.purchase_history[-50:]
        
        logger.info(f"記錄購買: {opportunity.item.item_name} - 利潤率: {opportunity.profit_potential:.1%}")

    def get_strategy_statistics(self) -> Dict[str, any]:
        """獲取策略統計信息"""
        if not self.purchase_history:
            return {"total_purchases": 0, "avg_profit_margin": 0.0}
        
        recent_purchases = self.purchase_history[-20:]  # 最近20次購買
        
        return {
            "total_purchases": len(self.purchase_history),
            "recent_purchases": len(recent_purchases),
            "recent_avg_profit_margin": sum(p.profit_potential for p in recent_purchases) / len(recent_purchases),
            "target_items_purchased": len([
                p for p in recent_purchases 
                if p.item.item_name in self.trading_config.market_search.target_items
            ])
        } 