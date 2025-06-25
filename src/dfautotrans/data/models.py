"""Data models for Dead Frontier Auto Trading System."""

from datetime import datetime
from typing import Optional, List
from enum import Enum
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field
from decimal import Decimal
from dataclasses import dataclass

Base = declarative_base()


class TradeType(str, Enum):
    """Trade types."""
    BUY = "buy"
    SELL = "sell"


class TradeStatus(str, Enum):
    """Trade status."""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MarketItem(Base):
    """Market item database model."""
    __tablename__ = "market_items"
    
    id = Column(Integer, primary_key=True)
    item_name = Column(String(255), nullable=False)
    seller = Column(String(100), nullable=False)
    trade_zone = Column(String(50))
    price = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False)
    discovered_at = Column(DateTime, default=datetime.utcnow)
    buy_item_location = Column(String(50))  # data-item-location from MCP tests
    buy_num = Column(String(50))  # data-buynum from MCP tests
    
    # Relationships
    trades = relationship("Trade", back_populates="market_item")


class Trade(Base):
    """Trade record database model."""
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("trading_sessions.id"))
    market_item_id = Column(Integer, ForeignKey("market_items.id"))
    trade_type = Column(String(10), nullable=False)  # buy/sell
    status = Column(String(20), default=TradeStatus.PENDING)
    quantity = Column(Integer, nullable=False)
    price_per_unit = Column(Float, nullable=False)
    total_amount = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    error_message = Column(Text)
    
    # Additional fields for compatibility
    item_name = Column(String(255))
    buy_price = Column(Float)
    sell_price = Column(Float)
    profit = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)
    seller = Column(String(255))
    buyer = Column(String(255))
    
    # Relationships
    market_item = relationship("MarketItem", back_populates="trades")


class UserProfile(Base):
    """User profile database model."""
    __tablename__ = "user_profiles"
    
    id = Column(Integer, primary_key=True)
    username = Column(String(100), nullable=False, unique=True)
    character_name = Column(String(100))
    profession = Column(String(50))
    level = Column(Integer)
    cash = Column(Integer, default=0)
    bank = Column(Integer, default=0)
    credits = Column(Integer, default=0)
    health = Column(String(20))
    hunger = Column(String(20))
    last_updated = Column(DateTime, default=datetime.utcnow)


class MarketPrice(Base):
    """Market price history database model."""
    __tablename__ = "market_prices"
    
    id = Column(Integer, primary_key=True)
    item_name = Column(String(255), nullable=False)
    price = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False)
    seller = Column(String(255), nullable=False)
    condition = Column(String(50))
    timestamp = Column(DateTime, default=datetime.utcnow)


class TradingSession(Base):
    """Trading session database model."""
    __tablename__ = "trading_sessions"
    
    id = Column(Integer, primary_key=True)
    session_start = Column(DateTime, default=datetime.utcnow)
    session_end = Column(DateTime)
    total_trades = Column(Integer, default=0)
    successful_trades = Column(Integer, default=0)
    failed_trades = Column(Integer, default=0)
    total_profit = Column(Float, default=0.0)
    session_notes = Column(Text)
    # Add fields for new functionality
    is_active = Column(Boolean, default=True)
    initial_cash = Column(Integer, default=0)
    final_cash = Column(Integer, default=0)
    state = Column(String(50), default="idle")


# Pydantic models for API/data validation
class MarketItemData(BaseModel):
    """Market item data model."""
    item_name: str
    seller: str
    trade_zone: Optional[str] = None
    price: float
    quantity: int
    buy_item_location: Optional[str] = None
    buy_num: Optional[str] = None


class TradeData(BaseModel):
    """Trade data model."""
    trade_type: TradeType
    item_name: str
    seller: str
    quantity: int
    price_per_unit: float
    total_amount: float


class UserProfileData(BaseModel):
    """User profile data model."""
    username: str
    character_name: Optional[str] = None
    profession: Optional[str] = None
    level: Optional[int] = None
    cash: int = 0
    bank: int = 0
    credits: int = 0
    health: Optional[str] = None
    hunger: Optional[str] = None


class InventoryItemData(BaseModel):
    """Inventory item data model."""
    item_name: str
    quantity: int
    location: str  # "inventory", "storage", "selling"
    condition: Optional[str] = None
    purchase_price: Optional[float] = None
    acquired_date: Optional[datetime] = None


class SellingSlotsStatus(BaseModel):
    """Selling slots status (e.g., 6/30)."""
    current_listings: int
    max_slots: int
    listed_items: List[str] = Field(default_factory=list)
    
    @property
    def is_full(self) -> bool:
        return self.current_listings >= self.max_slots
    
    @property
    def available_slots(self) -> int:
        return max(0, self.max_slots - self.current_listings)


class InventoryStatus(BaseModel):
    """Inventory status model."""
    current_count: int
    max_capacity: int
    
    @property
    def is_full(self) -> bool:
        return self.current_count >= self.max_capacity
    
    @property
    def available_space(self) -> int:
        return max(0, self.max_capacity - self.current_count)
    
    @property
    def utilization_rate(self) -> float:
        if self.max_capacity == 0:
            return 0.0
        return self.current_count / self.max_capacity


class StorageStatus(BaseModel):
    """Storage status model."""
    current_count: int
    max_capacity: int
    
    @property
    def is_full(self) -> bool:
        return self.current_count >= self.max_capacity
    
    @property
    def available_space(self) -> int:
        return max(0, self.max_capacity - self.current_count)
    
    @property
    def utilization_rate(self) -> float:
        if self.max_capacity == 0:
            return 0.0
        return self.current_count / self.max_capacity


class PlayerResources(BaseModel):
    """Complete player resources information."""
    cash_on_hand: int
    bank_balance: int
    inventory_status: InventoryStatus
    storage_status: StorageStatus
    selling_slots_status: SellingSlotsStatus
    
    @property
    def total_available_cash(self) -> int:
        """Total available cash (hand + bank)."""
        return self.cash_on_hand + self.bank_balance
    
    @property
    def has_sufficient_funds(self) -> bool:
        """Check if player has sufficient funds for trading (at least $1000)."""
        return self.total_available_cash >= 1000
    
    @property
    def has_inventory_space(self) -> bool:
        """Check if player has inventory space available."""
        return not self.inventory_status.is_full
    
    @property
    def has_storage_space(self) -> bool:
        """Check if player has storage space available."""
        return not self.storage_status.is_full
    
    @property
    def has_selling_slots(self) -> bool:
        """Check if player has selling slots available."""
        return not self.selling_slots_status.is_full


class TradingSystemStatus(BaseModel):
    """Trading system status information."""
    current_state: 'TradingState'
    player_resources: Optional[PlayerResources] = None
    last_state_change: datetime
    wait_until: Optional[datetime] = None
    retry_count: int = 0
    
    @property
    def is_waiting(self) -> bool:
        """Check if system is in a wait condition."""
        if self.wait_until is None:
            return False
        return datetime.utcnow() < self.wait_until
    
    @property
    def wait_remaining_seconds(self) -> int:
        """Get remaining wait time in seconds."""
        if self.wait_until is None:
            return 0
        remaining = (self.wait_until - datetime.utcnow()).total_seconds()
        return max(0, int(remaining))
    
    @property
    def current_state_duration_seconds(self) -> float:
        """Get duration of current state in seconds."""
        return (datetime.utcnow() - self.last_state_change).total_seconds()


class SearchResult(BaseModel):
    """Search result from marketplace."""
    items: List[MarketItemData]
    total_found: int
    search_term: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class TradingOpportunity(BaseModel):
    """Trading opportunity analysis."""
    item: MarketItemData
    potential_profit: float
    profit_margin: float
    risk_score: float
    recommended_action: str
    confidence: float


# Extended models for the new trading workflow
class TradingState(Enum):
    """交易系統狀態枚舉"""
    # 基礎狀態
    IDLE = "idle"
    INITIALIZING = "initializing"
    
    # 登錄狀態
    LOGIN_REQUIRED = "login_required"
    LOGGING_IN = "logging_in"
    LOGIN_FAILED = "login_failed"
    
    # 資源檢查狀態
    CHECKING_RESOURCES = "checking_resources"
    INSUFFICIENT_FUNDS = "insufficient_funds"
    WITHDRAWING_FROM_BANK = "withdrawing_from_bank"
    
    # 空間管理狀態
    CHECKING_INVENTORY = "checking_inventory"
    DEPOSITING_TO_STORAGE = "depositing_to_storage"
    SPACE_FULL = "space_full"
    
    # 交易狀態
    MARKET_SCANNING = "market_scanning"
    BUYING = "buying"
    SELLING = "selling"
    
    # 等待狀態
    WAITING_NORMAL = "waiting_normal"
    WAITING_BLOCKED = "waiting_blocked"
    
    # 錯誤狀態
    ERROR = "error"
    CRITICAL_ERROR = "critical_error"


class TradingCycle(Enum):
    """交易週期枚舉"""
    LOGIN_CHECK = "login_check"
    RESOURCE_CHECK = "resource_check"
    SPACE_MANAGEMENT = "space_management"
    MARKET_ANALYSIS = "market_analysis"
    BUYING_PHASE = "buying_phase"
    SELLING_PHASE = "selling_phase"
    WAIT_PHASE = "wait_phase"
    ERROR_HANDLING = "error_handling"


@dataclass
class PurchaseOpportunity:
    """購買機會數據"""
    item: MarketItemData
    profit_potential: float  # 預期利潤率
    priority_score: float    # 優先級評分
    estimated_sell_price: float  # 預期銷售價格
    risk_level: str         # 風險等級: "low", "medium", "high"
    
    def __post_init__(self):
        """驗證數據完整性"""
        if self.profit_potential < 0:
            raise ValueError("利潤潛力不能為負數")
        if self.priority_score < 0:
            raise ValueError("優先級評分不能為負數")
        if self.estimated_sell_price <= 0:
            raise ValueError("預期銷售價格必須大於0")


@dataclass
class SellOrder:
    """銷售訂單數據"""
    item: InventoryItemData
    selling_price: float
    priority_score: float
    slot_position: Optional[int] = None  # 銷售位編號
    
    def __post_init__(self):
        """驗證數據完整性"""
        if self.selling_price <= 0:
            raise ValueError("銷售價格必須大於0")
        if self.priority_score < 0:
            raise ValueError("優先級評分不能為負數")


@dataclass
class TradingSession:
    """交易會話數據"""
    session_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    current_state: TradingState = TradingState.IDLE
    current_cycle: Optional[TradingCycle] = None
    
    # 統計數據
    total_purchases: int = 0
    total_sales: int = 0
    total_profit: float = 0.0
    successful_transactions: int = 0
    failed_transactions: int = 0
    
    # 錯誤統計
    login_failures: int = 0
    network_errors: int = 0
    business_errors: int = 0
    
    def __post_init__(self):
        """初始化會話ID"""
        if not self.session_id:
            self.session_id = f"session_{self.start_time.strftime('%Y%m%d_%H%M%S')}"


@dataclass
class MarketCondition:
    """市場狀況數據"""
    total_items_scanned: int
    valuable_opportunities: int
    average_profit_margin: float
    market_activity_level: str  # "low", "medium", "high"
    last_scan_time: datetime
    
    def __post_init__(self):
        """驗證數據"""
        if self.total_items_scanned < 0:
            raise ValueError("掃描物品數量不能為負數")
        if self.valuable_opportunities < 0:
            raise ValueError("有價值機會數量不能為負數")


@dataclass
class SystemResources:
    """系統資源狀況"""
    current_cash: int
    bank_balance: int
    total_funds: int
    inventory_used: int
    inventory_total: int
    storage_used: int
    storage_total: int
    selling_slots_used: int
    selling_slots_total: int
    
    @property
    def inventory_space_available(self) -> int:
        """可用庫存空間"""
        return max(0, self.inventory_total - self.inventory_used)
    
    @property
    def storage_space_available(self) -> int:
        """可用倉庫空間"""
        return max(0, self.storage_total - self.storage_used)
    
    @property
    def selling_slots_available(self) -> int:
        """可用銷售位"""
        return max(0, self.selling_slots_total - self.selling_slots_used)
    
    @property
    def is_funds_sufficient(self) -> bool:
        """資金是否充足（至少$1000）"""
        return self.total_funds >= 1000
    
    @property
    def is_space_available(self) -> bool:
        """是否有可用空間"""
        return (self.inventory_space_available > 0 or 
                self.storage_space_available > 0)
    
    @property
    def is_completely_blocked(self) -> bool:
        """是否完全阻塞（無資金、無空間、無銷售位）"""
        return (not self.is_funds_sufficient and 
                not self.is_space_available and 
                self.selling_slots_available == 0)


@dataclass
class TradingConfiguration:
    """交易配置參數"""
    # 購買策略參數
    min_profit_margin: float = 0.15  # 最小利潤率15%
    max_item_price: float = 50000.0  # 最大單件物品價格
    max_total_investment: float = 100000.0  # 最大總投資額
    
    # 風險管理參數
    max_high_risk_purchases: int = 3  # 最多高風險購買數量
    diversification_limit: int = 5   # 同類物品最大購買數量
    
    # 時間管理參數
    normal_wait_seconds: int = 60     # 正常等待時間
    blocked_wait_seconds: int = 300   # 阻塞等待時間
    login_retry_wait_seconds: int = 30  # 登錄重試等待時間
    
    # 重試參數
    max_retries: int = 3              # 最大重試次數
    max_login_retries: int = 5        # 最大登錄重試次數
    
    def __post_init__(self):
        """驗證配置參數"""
        if self.min_profit_margin <= 0:
            raise ValueError("最小利潤率必須大於0")
        if self.max_item_price <= 0:
            raise ValueError("最大物品價格必須大於0")
        if self.max_total_investment <= 0:
            raise ValueError("最大總投資額必須大於0")


# Database models for state persistence
class SystemState(Base):
    """System state persistence."""
    __tablename__ = "system_states"
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    current_state = Column(String(50), nullable=False)
    previous_state = Column(String(50))
    state_data = Column(Text)  # JSON serialized data
    session_id = Column(Integer, ForeignKey("trading_sessions.id"))
    error_message = Column(Text)


class ResourceSnapshot(Base):
    """Player resources snapshot."""
    __tablename__ = "resource_snapshots"
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    cash_on_hand = Column(Integer, default=0)
    bank_balance = Column(Integer, default=0)
    inventory_count = Column(Integer, default=0)
    inventory_capacity = Column(Integer, default=0)
    storage_count = Column(Integer, default=0)
    storage_capacity = Column(Integer, default=0)
    selling_slots_used = Column(Integer, default=0)
    selling_slots_max = Column(Integer, default=30)
    session_id = Column(Integer, ForeignKey("trading_sessions.id")) 