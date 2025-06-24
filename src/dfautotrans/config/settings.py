"""Configuration management for Dead Frontier Auto Trading System."""

import os
from typing import List, Optional
from pathlib import Path
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class DatabaseConfig(BaseModel):
    """Database configuration."""
    url: str = Field(default="sqlite:///dfautotrans.db")


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = Field(default="INFO")
    file: str = Field(default="dfautotrans.log")


class BrowserConfig(BaseModel):
    """Browser configuration."""
    headless: bool = Field(default=False)
    slow_mo: int = Field(default=100)
    timeout: int = Field(default=30000)
    viewport_width: int = Field(default=1920)
    viewport_height: int = Field(default=1080)


class TradingConfig(BaseModel):
    """Trading configuration."""
    # 交易目標和策略
    target_items: List[str] = Field(default=["12.7mm Rifle Bullets"])
    max_price_per_unit: float = Field(default=11.6)
    sell_price_multiplier: float = Field(default=1.01)
    min_profit_margin: float = Field(default=0.15)
    
    # 資金管理
    minimum_cash_threshold: int = Field(default=5000, description="最低資金界線，低於此值不執行交易")
    max_investment: int = Field(default=1000000)
    max_daily_trades: int = Field(default=100)
    auto_withdraw_from_bank: bool = Field(default=True, description="是否自動從bank取錢")
    
    # 空間和上架管理
    max_selling_slots: int = Field(default=30, description="最大上架貨品數量")
    auto_deposit_to_storage: bool = Field(default=True, description="是否自動將inventory存入storage")
    inventory_management_enabled: bool = Field(default=True, description="是否啟用自動inventory管理")
    
    # 市場刷新策略
    market_refresh_interval: int = Field(default=60, description="正常市場刷新間隔(秒)")
    market_wait_when_blocked: int = Field(default=300, description="完全阻塞時等待間隔(秒)")
    max_wait_cycles: int = Field(default=10, description="最大等待週期數")


class RiskManagementConfig(BaseModel):
    """Risk management configuration."""
    stop_loss_percentage: float = Field(default=0.2)
    max_items_per_type: int = Field(default=10)
    diversification_threshold: float = Field(default=0.3)
    emergency_stop_enabled: bool = Field(default=True)


class AntiDetectionConfig(BaseModel):
    """Anti-detection configuration."""
    mouse_movement_variation: float = Field(default=0.3)
    typing_delay_min: int = Field(default=50)
    typing_delay_max: int = Field(default=150)
    action_delay_min: int = Field(default=300)
    action_delay_max: int = Field(default=800)
    random_pause_probability: float = Field(default=0.1)


class Settings(BaseModel):
    """Main application settings."""
    
    # Core configurations
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    browser: BrowserConfig = Field(default_factory=BrowserConfig)
    trading: TradingConfig = Field(default_factory=TradingConfig)
    risk_management: RiskManagementConfig = Field(default_factory=RiskManagementConfig)
    anti_detection: AntiDetectionConfig = Field(default_factory=AntiDetectionConfig)
    
    # Dead Frontier specific URLs
    login_url: str = Field(default="https://www.deadfrontier.com/index.php?autologin=1")
    home_url: str = Field(default="https://fairview.deadfrontier.com/onlinezombiemmo/index.php")
    marketplace_url: str = Field(default="https://fairview.deadfrontier.com/onlinezombiemmo/index.php?page=35")
    bank_url: str = Field(default="https://fairview.deadfrontier.com/onlinezombiemmo/index.php?page=15")
    storage_url: str = Field(default="https://fairview.deadfrontier.com/onlinezombiemmo/index.php?page=50")
    
    # Login credentials
    username: str = Field(default="to6606687")
    password: str = Field(default="To38044567")
    
    def __init__(self, **kwargs):
        # Override with environment variables
        env_overrides = {
            "database": DatabaseConfig(
                url=os.getenv("DATABASE_URL", "sqlite:///dfautotrans.db")
            ),
            "logging": LoggingConfig(
                level=os.getenv("LOG_LEVEL", "INFO"),
                file=os.getenv("LOG_FILE", "dfautotrans.log")
            ),
            "browser": BrowserConfig(
                headless=os.getenv("HEADLESS", "false").lower() == "true",
                slow_mo=int(os.getenv("SLOW_MO", "100")),
                timeout=int(os.getenv("TIMEOUT", "30000"))
            ),
            "trading": TradingConfig(
                target_items=os.getenv("TARGET_ITEMS", "12.7mm Rifle Bullets").split(",") if os.getenv("TARGET_ITEMS") else ["12.7mm Rifle Bullets"],
                max_price_per_unit=float(os.getenv("MAX_PRICE_PER_UNIT", "11.6")),
                sell_price_multiplier=float(os.getenv("SELL_PRICE_MULTIPLIER", "1.01")),
                max_investment=int(os.getenv("MAX_INVESTMENT", "1000000")),
                min_profit_margin=float(os.getenv("MIN_PROFIT_MARGIN", "0.15")),
                max_daily_trades=int(os.getenv("MAX_DAILY_TRADES", "100"))
            ),
            "risk_management": RiskManagementConfig(
                stop_loss_percentage=float(os.getenv("STOP_LOSS_PERCENTAGE", "0.2")),
                max_items_per_type=int(os.getenv("MAX_ITEMS_PER_TYPE", "10")),
                diversification_threshold=float(os.getenv("DIVERSIFICATION_THRESHOLD", "0.3")),
                emergency_stop_enabled=os.getenv("EMERGENCY_STOP_ENABLED", "true").lower() == "true"
            ),
            "anti_detection": AntiDetectionConfig(
                mouse_movement_variation=float(os.getenv("MOUSE_MOVEMENT_VARIATION", "0.3")),
                typing_delay_min=int(os.getenv("TYPING_DELAY_MIN", "50")),
                typing_delay_max=int(os.getenv("TYPING_DELAY_MAX", "150")),
                action_delay_min=int(os.getenv("ACTION_DELAY_MIN", "300")),
                action_delay_max=int(os.getenv("ACTION_DELAY_MAX", "800")),
                random_pause_probability=float(os.getenv("RANDOM_PAUSE_PROBABILITY", "0.1"))
            ),
            # Login credentials from environment or defaults
            "username": os.getenv("DF_USERNAME", "to6606687"),
            "password": os.getenv("DF_PASSWORD", "To38044567")
        }
        
        super().__init__(**{**env_overrides, **kwargs})
    
    @property
    def project_root(self) -> Path:
        """Get project root directory."""
        return Path(__file__).parent.parent.parent.parent
    
    @property
    def data_dir(self) -> Path:
        """Get data directory."""
        data_dir = self.project_root / "data"
        data_dir.mkdir(exist_ok=True)
        return data_dir
    
    @property
    def logs_dir(self) -> Path:
        """Get logs directory."""
        logs_dir = self.project_root / "logs"
        logs_dir.mkdir(exist_ok=True)
        return logs_dir 