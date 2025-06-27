"""
交易配置管理模組
處理所有交易相關的配置參數
"""

import json
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

@dataclass
class MarketSearchConfig:
    """市場搜索配置"""
    target_items: List[str]  # 目標物品清單，精確匹配
    max_price_per_unit: List[float]  # 每種物品的最大購買價格（與target_items對應）
    max_items_per_search: int = 75
    search_timeout_seconds: int = 30

    @property
    def primary_search_terms(self) -> List[str]:
        """返回目標物品清單作為搜索詞 - 向後兼容"""
        return self.target_items

@dataclass
class BuyingConfig:
    """購買策略配置"""
    min_profit_margin: float = 0.15  # 最小利潤率
    max_purchases_per_cycle: int = 10
    diversification_enabled: bool = True
    priority_items: Dict[str, int] = None  # 物品優先級
    price_analysis_samples: int = 20

    def __post_init__(self):
        if self.priority_items is None:
            self.priority_items = {}
    
    # 向後兼容的屬性
    @property
    def max_total_investment(self) -> float:
        """最大總投資額 - 向後兼容"""
        return 100000.0
    
    @property
    def max_item_price(self) -> float:
        """最大單件物品價格 - 向後兼容"""
        return 50000.0
    
    @property
    def max_high_risk_purchases(self) -> int:
        """最多高風險購買數量 - 向後兼容"""
        return 3
    
    @property
    def diversification_limit(self) -> int:
        """同類物品最大購買數量 - 向後兼容"""
        return 5

@dataclass
class SellingConfig:
    """銷售策略配置"""
    markup_percentage: float = 0.2  # 標準加價比例
    min_markup_percentage: float = 0.1
    max_markup_percentage: float = 0.5
    max_inventory_slots_used: int = 25
    inventory_threshold_percentage: float = 0.8
    max_selling_slots_used: int = 25
    selling_slots_threshold_percentage: float = 0.95
    price_adjustment_enabled: bool = True

@dataclass
class RiskManagementConfig:
    """風險管理配置"""
    max_consecutive_failures: int = 3
    failure_cooldown_minutes: int = 5
    anti_detection_enabled: bool = True
    random_delay_range: Tuple[int, int] = (2, 8)
    max_operations_per_hour: int = 50
    
    # 向後兼容的屬性
    @property
    def normal_wait_seconds(self) -> int:
        """正常等待時間 - 向後兼容"""
        return 60
    
    @property
    def blocked_wait_seconds(self) -> int:
        """阻塞等待時間 - 向後兼容"""
        return 300
    
    @property
    def login_retry_wait_seconds(self) -> int:
        """登錄重試等待時間 - 向後兼容"""
        return 30
    
    @property
    def max_retries(self) -> int:
        """最大重試次數 - 向後兼容"""
        return 3
    
    @property
    def max_login_retries(self) -> int:
        """最大登錄重試次數 - 向後兼容"""
        return 5

@dataclass
class PerformanceConfig:
    """性能優化配置"""
    market_cache_duration_minutes: int = 1
    price_cache_duration_minutes: int = 1
    operation_timeout_seconds: int = 60
    max_retries: int = 3
    retry_delay_seconds: int = 5
    exponential_backoff: bool = True

@dataclass
class TradingConfig:
    """完整交易配置"""
    market_search: MarketSearchConfig
    buying: BuyingConfig
    selling: SellingConfig
    risk_management: RiskManagementConfig
    performance: PerformanceConfig
    
    # 全局設置
    trading_enabled: bool = True
    debug_mode: bool = False
    dry_run_mode: bool = False
    max_trading_cycles: int = 0
    cycle_interval_minutes: int = 10
    session_timeout_hours: int = 8
    detailed_logging: bool = True
    log_all_market_data: bool = False

class TradingConfigManager:
    """交易配置管理器"""
    
    def __init__(self, config_file: str = "trading_config.json"):
        self.config_file = Path(config_file)
        self.config: Optional[TradingConfig] = None
        
    def load_config(self) -> TradingConfig:
        """載入配置"""
        try:
            if not self.config_file.exists():
                logger.warning(f"配置文件 {self.config_file} 不存在，使用默認配置")
                self.config = self._create_default_config()
                self.save_config()
                return self.config
                
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # 轉換為配置對象
            self.config = self._dict_to_config(data)
            
            # 驗證配置
            self.validate_config()
            
            logger.info("配置載入成功")
            return self.config
            
        except Exception as e:
            logger.error(f"載入配置失敗: {e}")
            logger.info("使用默認配置")
            self.config = self._create_default_config()
            return self.config
    
    def save_config(self) -> bool:
        """保存配置"""
        try:
            if not self.config:
                logger.error("沒有配置可保存")
                return False
                
            data = self._config_to_dict(self.config)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
            logger.info(f"配置已保存到 {self.config_file}")
            return True
            
        except Exception as e:
            logger.error(f"保存配置失敗: {e}")
            return False
    
    def update_config(self, updates: Dict[str, Any]) -> bool:
        """動態更新配置"""
        try:
            if not self.config:
                self.load_config()
                
            for key, value in updates.items():
                self._set_nested_value(self.config, key, value)
                
            # 重新驗證配置
            self.validate_config()
            
            logger.info(f"配置更新成功: {list(updates.keys())}")
            return True
            
        except Exception as e:
            logger.error(f"更新配置失敗: {e}")
            print(f"更新配置失敗: {e}")  # 也輸出到控制台
            return False
    
    def validate_config(self) -> bool:
        """驗證配置有效性"""
        if not self.config:
            raise ValueError("配置未載入")
            
        # 驗證目標物品和價格數組長度一致
        market_config = self.config.market_search
        if len(market_config.target_items) != len(market_config.max_price_per_unit):
            raise ValueError(
                f"target_items 長度 ({len(market_config.target_items)}) "
                f"與 max_price_per_unit 長度 ({len(market_config.max_price_per_unit)}) 不一致"
            )
            
        # 驗證價格為正數
        for i, price in enumerate(market_config.max_price_per_unit):
            if price <= 0:
                raise ValueError(f"max_price_per_unit[{i}] 必須大於 0，當前值: {price}")
                
        # 驗證利潤率
        if not 0 < self.config.buying.min_profit_margin < 1:
            raise ValueError(f"min_profit_margin 必須在 0-1 之間，當前值: {self.config.buying.min_profit_margin}")
            
            
        # 驗證延遲範圍
        delay_range = self.config.risk_management.random_delay_range
        if delay_range[0] >= delay_range[1]:
            raise ValueError(f"random_delay_range 最小值必須小於最大值，當前值: {delay_range}")
            
        logger.info("配置驗證通過")
        return True
    
    def get_item_max_price(self, item_name: str) -> Optional[float]:
        """獲取指定物品的最大價格"""
        if not self.config:
            return None
            
        try:
            index = self.config.market_search.target_items.index(item_name)
            return self.config.market_search.max_price_per_unit[index]
        except (ValueError, IndexError):
            return None
    
    def get_item_priority(self, item_name: str) -> int:
        """獲取物品優先級"""
        if not self.config:
            return 999
            
        return self.config.buying.priority_items.get(item_name, 999)
    
    def is_target_item(self, item_name: str) -> bool:
        """檢查是否為目標物品"""
        if not self.config:
            return False
            
        return item_name in self.config.market_search.target_items
    
    def get_item_id_by_name(self, item_name: str) -> Optional[str]:
        """根據物品名稱獲取data-type ID"""
        if not self.config_file.exists():
            return None
            
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get("item_mapping", {}).get("name_to_id", {}).get(item_name)
        except:
            return None
    
    def get_item_name_by_id(self, item_id: str) -> Optional[str]:
        """根據data-type ID獲取物品名稱"""
        if not self.config_file.exists():
            return None
            
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get("item_mapping", {}).get("id_to_name", {}).get(item_id)
        except:
            return None
    
    def get_item_mapping(self) -> Dict[str, str]:
        """獲取物品名稱到ID的映射"""
        if not self.config_file.exists():
            return {}
            
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get("item_mapping", {}).get("name_to_id", {})
        except:
            return {}
    
    def _create_default_config(self) -> TradingConfig:
        """創建默認配置"""
        return TradingConfig(
            market_search=MarketSearchConfig(
                target_items=["12.7mm Rifle Bullets", "14mm Rifle Bullets", "9mm Rifle Bullets", "10 Gauge Shells", "12 Gauge Shells", "Energy Cell", "Gasoline"],
                max_price_per_unit=[11.0, 13.0, 11.0, 15.0, 16.0, 15.0, 3.0],
                max_items_per_search=13,
                search_timeout_seconds=15
            ),
            buying=BuyingConfig(
                priority_items={
                    "12.7mm Rifle Bullets": 1,
                    "14mm Rifle Bullets": 2,
                    "9mm Rifle Bullets": 3,
                    "10 Gauge Shells": 4,
                    "12 Gauge Shells": 5,
                    "Energy Cell": 6,
                    "Gasoline": 7
                }
            ),
            selling=SellingConfig(),
            risk_management=RiskManagementConfig(),
            performance=PerformanceConfig()
        )
    
    def _dict_to_config(self, data: Dict[str, Any]) -> TradingConfig:
        """將字典轉換為配置對象"""
        # 處理特殊的tuple類型
        if 'risk_management' in data and 'random_delay_range' in data['risk_management']:
            delay_range = data['risk_management']['random_delay_range']
            if isinstance(delay_range, list):
                data['risk_management']['random_delay_range'] = tuple(delay_range)
        
        return TradingConfig(
            market_search=MarketSearchConfig(**data.get('market_search', {})),
            buying=BuyingConfig(**data.get('buying', {})),
            selling=SellingConfig(**data.get('selling', {})),
            risk_management=RiskManagementConfig(**data.get('risk_management', {})),
            performance=PerformanceConfig(**data.get('performance', {})),
            trading_enabled=data.get('trading_enabled', True),
            debug_mode=data.get('debug_mode', False),
            dry_run_mode=data.get('dry_run_mode', False),
            max_trading_cycles=data.get('max_trading_cycles', 10),
            cycle_interval_minutes=data.get('cycle_interval_minutes', 30),
            session_timeout_hours=data.get('session_timeout_hours', 8),
            detailed_logging=data.get('detailed_logging', True),
            log_all_market_data=data.get('log_all_market_data', False)
        )
    
    def _config_to_dict(self, config: TradingConfig) -> Dict[str, Any]:
        """將配置對象轉換為字典"""
        data = asdict(config)
        
        # 處理tuple轉換為list以便JSON序列化
        if 'risk_management' in data and 'random_delay_range' in data['risk_management']:
            data['risk_management']['random_delay_range'] = list(data['risk_management']['random_delay_range'])
            
        return data
    
    def _set_nested_value(self, obj: Any, key: str, value: Any):
        """設置嵌套對象的值"""
        keys = key.split('.')
        current = obj
        
        for k in keys[:-1]:
            current = getattr(current, k)
            
        setattr(current, keys[-1], value)
    
    def print_config_summary(self):
        """打印配置摘要"""
        if not self.config:
            print("配置未載入")
            return
            
        print("\n=== 交易配置摘要 ===")
        
        # 市場搜索配置
        print(f"\n📊 市場搜索配置:")
        print(f"  目標物品數量: {len(self.config.market_search.target_items)}")
        for i, (item, price) in enumerate(zip(self.config.market_search.target_items, 
                                             self.config.market_search.max_price_per_unit)):
            print(f"  {i+1}. {item}: 最高 ${price}")
        
        # 購買配置
        print(f"\n💰 購買策略:")
        print(f"  最小利潤率: {self.config.buying.min_profit_margin:.1%}")
        print(f"  每週期最大購買: {self.config.buying.max_purchases_per_cycle}")
        print(f"  多樣化投資: {'啟用' if self.config.buying.diversification_enabled else '禁用'}")
        print(f"  價格分析樣本: {self.config.buying.price_analysis_samples}")
        
        # 銷售配置
        print(f"\n📈 銷售策略:")
        print(f"  標準加價: {self.config.selling.markup_percentage:.1%}")
        print(f"  動態調價: {'啟用' if self.config.selling.price_adjustment_enabled else '禁用'}")
        print(f"  最大庫存使用: {self.config.selling.max_inventory_slots_used} 位")
        print(f"  最大銷售位使用: {self.config.selling.max_selling_slots_used} 位")
        
        # 風險管理
        print(f"\n⚠️ 風險管理:")
        print(f"  反檢測: {'啟用' if self.config.risk_management.anti_detection_enabled else '禁用'}")
        print(f"  隨機延遲: {self.config.risk_management.random_delay_range[0]}-{self.config.risk_management.random_delay_range[1]} 秒")
        print(f"  每小時最大操作: {self.config.risk_management.max_operations_per_hour}")
        
        # 全局設置
        print(f"\n🌐 全局設置:")
        print(f"  交易啟用: {'是' if self.config.trading_enabled else '否'}")
        print(f"  調試模式: {'是' if self.config.debug_mode else '否'}")
        print(f"  模擬模式: {'是' if self.config.dry_run_mode else '否'}")
        print(f"  最大週期: {self.config.max_trading_cycles if self.config.max_trading_cycles > 0 else '無限制'}")
        
        print("\n" + "="*50)

# 全局配置管理器實例
config_manager = TradingConfigManager()

def load_config() -> TradingConfig:
    """載入配置的便捷函數"""
    return config_manager.load_config()

def get_config() -> Optional[TradingConfig]:
    """獲取當前配置"""
    if config_manager.config is None:
        config_manager.load_config()
    return config_manager.config

def update_config(updates: Dict[str, Any]) -> bool:
    """更新配置的便捷函數"""
    return config_manager.update_config(updates) 