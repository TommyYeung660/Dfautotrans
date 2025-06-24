"""Data models for Dead Frontier Auto Trading System."""

from datetime import datetime
from typing import Optional, List
from enum import Enum
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field

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
class TradingState(str, Enum):
    """Trading system states."""
    IDLE = "idle"
    INITIALIZING = "initializing"
    LOGIN_REQUIRED = "login_required"
    LOGGING_IN = "logging_in"
    LOGIN_FAILED = "login_failed"
    CHECKING_RESOURCES = "checking_resources"
    INSUFFICIENT_FUNDS = "insufficient_funds"
    WITHDRAWING_FROM_BANK = "withdrawing_from_bank"
    CHECKING_INVENTORY = "checking_inventory"
    DEPOSITING_TO_STORAGE = "depositing_to_storage"
    SPACE_FULL = "space_full"
    MARKET_SCANNING = "market_scanning"
    BUYING = "buying"
    SELLING = "selling"
    WAITING_NORMAL = "waiting_normal"
    WAITING_BLOCKED = "waiting_blocked"
    ERROR = "error"
    CRITICAL_ERROR = "critical_error"


class InventoryStatus(BaseModel):
    """Inventory space status."""
    current_count: int
    max_capacity: int
    items: List[str] = Field(default_factory=list)
    
    @property
    def is_full(self) -> bool:
        return self.current_count >= self.max_capacity
    
    @property
    def available_space(self) -> int:
        return max(0, self.max_capacity - self.current_count)
    
    @property
    def utilization_rate(self) -> float:
        return self.current_count / self.max_capacity if self.max_capacity > 0 else 0


class StorageStatus(BaseModel):
    """Storage space status."""
    current_count: int
    max_capacity: int
    items: List[str] = Field(default_factory=list)
    
    @property
    def is_full(self) -> bool:
        return self.current_count >= self.max_capacity
    
    @property
    def available_space(self) -> int:
        return max(0, self.max_capacity - self.current_count)


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


class PlayerResources(BaseModel):
    """Complete player resources status."""
    cash_on_hand: int
    bank_balance: int
    inventory_status: InventoryStatus
    storage_status: StorageStatus
    selling_slots_status: SellingSlotsStatus
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    @property
    def total_available_cash(self) -> int:
        return self.cash_on_hand + self.bank_balance
    
    @property
    def can_trade(self) -> bool:
        """Check if player has resources to execute trades."""
        return (self.total_available_cash > 0 and 
                not self.inventory_status.is_full)
    
    @property
    def is_completely_blocked(self) -> bool:
        """Check if player is completely blocked (no money, no space)."""
        return (self.total_available_cash == 0 and 
                self.inventory_status.is_full and 
                self.storage_status.is_full and 
                self.selling_slots_status.is_full)


class TradingSystemStatus(BaseModel):
    """Complete trading system status."""
    current_state: TradingState
    player_resources: PlayerResources
    last_state_change: datetime = Field(default_factory=datetime.utcnow)
    error_message: Optional[str] = None
    wait_until: Optional[datetime] = None
    retry_count: int = 0
    session_start: datetime = Field(default_factory=datetime.utcnow)


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