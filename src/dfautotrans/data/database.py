"""Database management for Dead Frontier Auto Trading System."""

import asyncio
from typing import Optional, List, Dict, Any, Type, TypeVar
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from loguru import logger

from .models import Base, TradingSession, Trade as TradeRecord, MarketPrice, SystemState, ResourceSnapshot
from ..config.settings import Settings

T = TypeVar('T', bound=Base)


class DatabaseManager:
    """Manages database connections and operations."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.database_url = settings.database.url
        
        # Convert SQLite URL to async if needed
        if self.database_url.startswith("sqlite://"):
            self.database_url = self.database_url.replace("sqlite://", "sqlite+aiosqlite://")
        
        self.engine = None
        self.async_session_factory = None
        self._initialized = False
        
        logger.info(f"Database manager initialized with URL: {self.database_url}")
    
    async def initialize(self) -> bool:
        """Initialize database engine and create tables."""
        try:
            # Create async engine
            self.engine = create_async_engine(
                self.database_url,
                echo=False,  # Set to True for SQL debugging
                pool_pre_ping=True,
                connect_args={"check_same_thread": False} if "sqlite" in self.database_url else {}
            )
            
            # Create session factory
            self.async_session_factory = async_sessionmaker(
                bind=self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # Create all tables
            await self.create_tables()
            
            # Test connection
            await self.test_connection()
            
            self._initialized = True
            logger.info("Database initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            return False
    
    async def create_tables(self) -> None:
        """Create all database tables."""
        try:
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            raise
    
    async def test_connection(self) -> bool:
        """Test database connection."""
        try:
            async with self.get_session() as session:
                result = await session.execute(text("SELECT 1"))
                result.fetchone()
            logger.debug("Database connection test successful")
            return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
    
    @asynccontextmanager
    async def get_session(self):
        """Get async database session context manager."""
        if not self._initialized or not self.async_session_factory:
            raise RuntimeError("Database not initialized")
        
        session = self.async_session_factory()
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()
    
    async def create_trading_session(self, initial_cash: int = 0) -> Optional[TradingSession]:
        """Create a new trading session."""
        try:
            async with self.get_session() as session:
                trading_session = TradingSession(
                    initial_cash=initial_cash,
                    state="idle"
                )
                session.add(trading_session)
                await session.flush()
                await session.refresh(trading_session)
                logger.info(f"Created trading session: {trading_session.id}")
                return trading_session
        except Exception as e:
            logger.error(f"Failed to create trading session: {e}")
            return None
    
    async def update_trading_session(self, session_id: int, **kwargs) -> bool:
        """Update trading session."""
        try:
            async with self.get_session() as session:
                result = await session.get(TradingSession, session_id)
                if result:
                    for key, value in kwargs.items():
                        if hasattr(result, key):
                            setattr(result, key, value)
                    logger.debug(f"Updated trading session {session_id}")
                    return True
                else:
                    logger.warning(f"Trading session {session_id} not found")
                    return False
        except Exception as e:
            logger.error(f"Failed to update trading session: {e}")
            return False
    
    async def get_active_trading_session(self) -> Optional[TradingSession]:
        """Get the currently active trading session."""
        try:
            async with self.get_session() as session:
                result = await session.execute(
                    text("SELECT * FROM trading_sessions WHERE is_active = 1 ORDER BY start_time DESC LIMIT 1")
                )
                row = result.fetchone()
                if row:
                    return TradingSession(**row._asdict())
                return None
        except Exception as e:
            logger.error(f"Failed to get active trading session: {e}")
            return None
    
    async def record_trade(self, trade_data: Dict[str, Any]) -> bool:
        """Record a trade transaction."""
        try:
            async with self.get_session() as session:
                trade_record = TradeRecord(**trade_data)
                session.add(trade_record)
                logger.debug(f"Recorded trade: {trade_data.get('item_name', 'Unknown')}")
                return True
        except Exception as e:
            logger.error(f"Failed to record trade: {e}")
            return False
    
    async def record_market_price(self, price_data: Dict[str, Any]) -> bool:
        """Record market price data."""
        try:
            async with self.get_session() as session:
                market_price = MarketPrice(**price_data)
                session.add(market_price)
                logger.debug(f"Recorded market price: {price_data.get('item_name', 'Unknown')}")
                return True
        except Exception as e:
            logger.error(f"Failed to record market price: {e}")
            return False
    
    async def save_system_state(self, state_data: Dict[str, Any]) -> bool:
        """Save system state to database."""
        try:
            async with self.get_session() as session:
                system_state = SystemState(**state_data)
                session.add(system_state)
                logger.debug(f"Saved system state: {state_data.get('current_state', 'Unknown')}")
                return True
        except Exception as e:
            logger.error(f"Failed to save system state: {e}")
            return False
    
    async def get_latest_system_state(self) -> Optional[SystemState]:
        """Get the latest system state."""
        try:
            async with self.get_session() as session:
                result = await session.execute(
                    text("SELECT * FROM system_states ORDER BY timestamp DESC LIMIT 1")
                )
                row = result.fetchone()
                if row:
                    return SystemState(**row._asdict())
                return None
        except Exception as e:
            logger.error(f"Failed to get latest system state: {e}")
            return None
    
    async def save_resource_snapshot(self, resource_data: Dict[str, Any]) -> bool:
        """Save player resources snapshot."""
        try:
            async with self.get_session() as session:
                resource_snapshot = ResourceSnapshot(**resource_data)
                session.add(resource_snapshot)
                logger.debug("Saved resource snapshot")
                return True
        except Exception as e:
            logger.error(f"Failed to save resource snapshot: {e}")
            return False
    
    async def get_recent_trades(self, limit: int = 10, session_id: Optional[int] = None) -> List[TradeRecord]:
        """Get recent trade records."""
        try:
            async with self.get_session() as session:
                query = "SELECT * FROM trades"
                params = {}
                
                if session_id:
                    query += " WHERE session_id = :session_id"
                    params["session_id"] = session_id
                
                query += " ORDER BY timestamp DESC LIMIT :limit"
                params["limit"] = limit
                
                result = await session.execute(text(query), params)
                rows = result.fetchall()
                
                return [TradeRecord(**row._asdict()) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get recent trades: {e}")
            return []
    
    async def get_market_price_history(
        self, 
        item_name: str, 
        hours: int = 24
    ) -> List[MarketPrice]:
        """Get market price history for an item."""
        try:
            async with self.get_session() as session:
                query = """
                SELECT * FROM market_prices 
                WHERE item_name = :item_name 
                AND timestamp > datetime('now', '-{} hours')
                ORDER BY timestamp DESC
                """.format(hours)
                
                result = await session.execute(text(query), {"item_name": item_name})
                rows = result.fetchall()
                
                return [MarketPrice(**row._asdict()) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get market price history: {e}")
            return []
    
    async def cleanup_old_data(self, days: int = 30) -> bool:
        """Clean up old data older than specified days."""
        try:
            async with self.get_session() as session:
                # Clean up old market prices
                await session.execute(
                    text("DELETE FROM market_prices WHERE timestamp < datetime('now', '-{} days')".format(days))
                )
                
                # Clean up old system states
                await session.execute(
                    text("DELETE FROM system_states WHERE timestamp < datetime('now', '-{} days')".format(days))
                )
                
                # Clean up old resource snapshots
                await session.execute(
                    text("DELETE FROM resource_snapshots WHERE timestamp < datetime('now', '-{} days')".format(days))
                )
                
                logger.info(f"Cleaned up data older than {days} days")
                return True
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")
            return False
    
    async def get_trading_statistics(self, session_id: Optional[int] = None) -> Dict[str, Any]:
        """Get trading statistics."""
        try:
            async with self.get_session() as session:
                # Base query
                base_query = "SELECT COUNT(*) as total_trades, SUM(profit) as total_profit FROM trades"
                params = {}
                
                if session_id:
                    base_query += " WHERE session_id = :session_id"
                    params["session_id"] = session_id
                
                result = await session.execute(text(base_query), params)
                stats = result.fetchone()
                
                return {
                    "total_trades": stats.total_trades or 0,
                    "total_profit": float(stats.total_profit) if stats.total_profit else 0.0,
                    "average_profit": float(stats.total_profit / stats.total_trades) if stats.total_trades else 0.0
                }
        except Exception as e:
            logger.error(f"Failed to get trading statistics: {e}")
            return {"total_trades": 0, "total_profit": 0.0, "average_profit": 0.0}
    
    async def close(self) -> None:
        """Close database connections."""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database connections closed")
    
    def __del__(self):
        """Cleanup on destruction."""
        if self.engine:
            try:
                # AsyncEngine doesn't have is_disposed attribute
                # Note: This might not work properly in async context
                logger.warning("Database engine not properly closed")
            except Exception:
                pass


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


async def get_db_manager(settings: Settings) -> DatabaseManager:
    """Get global database manager instance."""
    global _db_manager
    
    if _db_manager is None:
        _db_manager = DatabaseManager(settings)
        await _db_manager.initialize()
    
    return _db_manager


async def close_db_manager() -> None:
    """Close global database manager."""
    global _db_manager
    
    if _db_manager:
        await _db_manager.close()
        _db_manager = None 