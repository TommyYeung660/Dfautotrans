"""
Dead Frontier 自動交易系統 - 購買策略模組

這個模組負責分析市場物品並做出智能購買決策。
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
    """智能購買策略引擎"""
    
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
            self.trading_config = config_manager.get_config()
        
        # 向後兼容的配置屬性
        self.config = config
        self.item_history: Dict[str, List[float]] = {}  # 物品歷史價格
        self.purchase_history: List[PurchaseOpportunity] = []  # 購買歷史
        
        # 物品類型風險評級
        self.risk_categories = {
            "ammo": "low",      # 彈藥 - 低風險
            "weapon": "medium", # 武器 - 中風險
            "armor": "medium",  # 護甲 - 中風險
            "medical": "low",   # 醫療用品 - 低風險
            "food": "low",      # 食物 - 低風險
            "misc": "high",     # 雜項 - 高風險
        }
        
        # 熱門物品列表（基於經驗的高流動性物品）
        self.popular_items = {
            "12.7mm Rifle Bullets": {"base_price": 15.0, "demand": "high"},
            "7.62mm Rifle Bullets": {"base_price": 12.0, "demand": "high"},
            "5.56mm Rifle Bullets": {"base_price": 10.0, "demand": "high"},
            "12 Gauge Shells": {"base_price": 8.0, "demand": "medium"},
            "Pain Killers": {"base_price": 25.0, "demand": "high"},
            "Bandages": {"base_price": 15.0, "demand": "medium"},
        }
        
        # 更新熱門物品的優先級（從配置中獲取）
        priority_items = self.trading_config.buying.priority_items
        for item_name, priority in priority_items.items():
            if item_name in self.popular_items:
                self.popular_items[item_name]["priority"] = priority
        
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
        
        for item in items:
            try:
                # 基本過濾條件
                if not self._passes_basic_filters(item, resources):
                    continue
                
                # 計算購買機會
                opportunity = await self._evaluate_single_item(item, resources)
                if opportunity:
                    # 檢查投資限制
                    item_cost = item.price * item.quantity
                    max_investment = self.trading_config.buying.max_total_investment
                    if total_investment + item_cost <= max_investment:
                        opportunities.append(opportunity)
                        total_investment += item_cost
                        logger.debug(f"添加購買機會: {item.item_name} - 利潤率: {opportunity.profit_potential:.1%}")
                    else:
                        logger.debug(f"超出投資限制，跳過: {item.item_name}")
                        
            except Exception as e:
                logger.warning(f"評估物品時出錯 {item.item_name}: {e}")
                continue
        
        # 按優先級排序
        opportunities.sort(key=lambda x: x.priority_score, reverse=True)
        
        # 應用風險管理
        opportunities = self._apply_risk_management(opportunities)
        
        logger.info(f"評估完成，找到 {len(opportunities)} 個有價值的購買機會")
        return opportunities

    def _passes_basic_filters(self, item: MarketItemData, resources: SystemResources) -> bool:
        """檢查物品是否通過基本過濾條件"""
        
        # 價格過濾
        item_total_price = item.price * item.quantity
        if item_total_price > self.config.max_item_price:
            return False
        
        # 資金檢查
        if item_total_price > resources.total_funds:
            return False
        
        # 數量合理性檢查
        if item.quantity <= 0 or item.quantity > 10000:
            return False
        
        # 單價合理性檢查
        if item.price <= 0 or item.price > 100000:
            return False
        
        return True

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
            if profit_potential < self.config.min_profit_margin:
                return None
            
            # 風險評估
            risk_level = self._assess_risk_level(item)
            
            # 計算優先級評分
            priority_score = self._calculate_priority_score(
                item, profit_potential, risk_level
            )
            
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
        """估算物品的合理銷售價格"""
        
        # 基於熱門物品列表的估價
        if item.item_name in self.popular_items:
            base_info = self.popular_items[item.item_name]
            base_price = base_info["base_price"]
            demand_multiplier = 1.2 if base_info["demand"] == "high" else 1.1
            return base_price * demand_multiplier
        
        # 基於歷史價格的估價
        if item.item_name in self.item_history:
            history = self.item_history[item.item_name]
            if len(history) >= 3:
                avg_price = sum(history[-5:]) / len(history[-5:])  # 最近5次平均價格
                return avg_price * 1.1  # 10%加價
        
        # 基於物品類型的通用估價
        category = self._categorize_item(item.item_name)
        multipliers = {
            "ammo": 1.15,    # 彈藥通常有15%利潤空間
            "weapon": 1.25,  # 武器25%利潤空間
            "armor": 1.20,   # 護甲20%利潤空間
            "medical": 1.30, # 醫療用品30%利潤空間
            "food": 1.20,    # 食物20%利潤空間
            "misc": 1.50,    # 雜項50%利潤空間（高風險高回報）
        }
        
        return item.price * multipliers.get(category, 1.20)

    def _assess_risk_level(self, item: MarketItemData) -> str:
        """評估物品的風險等級"""
        
        category = self._categorize_item(item.item_name)
        base_risk = self.risk_categories.get(category, "medium")
        
        # 基於價格調整風險
        if item.price > 30000:
            if base_risk == "low":
                base_risk = "medium"
            elif base_risk == "medium":
                base_risk = "high"
        
        # 基於數量調整風險
        if item.quantity > 5000:
            if base_risk == "low":
                base_risk = "medium"
        
        return base_risk

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

    def _calculate_priority_score(
        self, 
        item: MarketItemData, 
        profit_potential: float, 
        risk_level: str
    ) -> float:
        """計算物品的優先級評分"""
        
        score = profit_potential * 100  # 基礎分數基於利潤率
        
        # 風險調整
        risk_multipliers = {"low": 1.2, "medium": 1.0, "high": 0.8}
        score *= risk_multipliers.get(risk_level, 1.0)
        
        # 熱門物品加分
        if item.item_name in self.popular_items:
            demand = self.popular_items[item.item_name]["demand"]
            if demand == "high":
                score *= 1.3
            elif demand == "medium":
                score *= 1.1
        
        # 數量合理性加分
        if 100 <= item.quantity <= 2000:
            score *= 1.1  # 合理數量加分
        elif item.quantity > 5000:
            score *= 0.9  # 數量過大減分
        
        # 價格合理性加分
        if 1000 <= (item.price * item.quantity) <= 30000:
            score *= 1.1  # 合理總價加分
        
        return score

    def _apply_risk_management(
        self, 
        opportunities: List[PurchaseOpportunity]
    ) -> List[PurchaseOpportunity]:
        """應用風險管理規則"""
        
        filtered_opportunities = []
        high_risk_count = 0
        item_type_counts: Dict[str, int] = {}
        
        for opportunity in opportunities:
            # 限制高風險購買數量
            if opportunity.risk_level == "high":
                if high_risk_count >= self.config.max_high_risk_purchases:
                    logger.debug(f"跳過高風險物品（已達上限）: {opportunity.item.item_name}")
                    continue
                high_risk_count += 1
            
            # 限制同類物品數量
            item_category = self._categorize_item(opportunity.item.item_name)
            current_count = item_type_counts.get(item_category, 0)
            if current_count >= self.config.diversification_limit:
                logger.debug(f"跳過同類物品（已達上限）: {opportunity.item.item_name}")
                continue
            
            item_type_counts[item_category] = current_count + 1
            filtered_opportunities.append(opportunity)
        
        logger.info(f"風險管理後保留 {len(filtered_opportunities)} 個購買機會")
        return filtered_opportunities

    def update_item_history(self, item_name: str, price: float):
        """更新物品歷史價格"""
        if item_name not in self.item_history:
            self.item_history[item_name] = []
        
        self.item_history[item_name].append(price)
        
        # 只保留最近20個價格記錄
        if len(self.item_history[item_name]) > 20:
            self.item_history[item_name] = self.item_history[item_name][-20:]

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
        
        # 只保留最近100個購買記錄
        if len(self.purchase_history) > 100:
            self.purchase_history = self.purchase_history[-100:]
        
        # 更新物品歷史價格
        self.update_item_history(
            opportunity.item.item_name, 
            opportunity.item.price
        )
        
        logger.info(f"記錄購買: {opportunity.item.item_name} - 利潤率: {opportunity.profit_potential:.1%}")

    def get_strategy_statistics(self) -> Dict[str, any]:
        """獲取策略統計信息"""
        if not self.purchase_history:
            return {"total_purchases": 0}
        
        recent_purchases = self.purchase_history[-20:]  # 最近20次購買
        
        return {
            "total_purchases": len(self.purchase_history),
            "recent_avg_profit_margin": sum(p.profit_potential for p in recent_purchases) / len(recent_purchases),
            "risk_distribution": {
                "low": len([p for p in recent_purchases if p.risk_level == "low"]),
                "medium": len([p for p in recent_purchases if p.risk_level == "medium"]),
                "high": len([p for p in recent_purchases if p.risk_level == "high"]),
            },
            "popular_items_purchased": len([
                p for p in recent_purchases 
                if p.item.item_name in self.popular_items
            ])
        } 