"""Tests for Stage 1: Infrastructure Implementation."""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from src.dfautotrans.config.settings import Settings
from src.dfautotrans.core.state_machine import StateMachine, StateTransitionError
from src.dfautotrans.core.page_navigator import PageNavigator, NavigationError
from src.dfautotrans.data.models import TradingState, InventoryStatus, PlayerResources, SellingSlotsStatus, StorageStatus
from src.dfautotrans.data.database import DatabaseManager
from src.dfautotrans.automation.browser_manager import BrowserManager


class TestStateMachine:
    """Test state machine functionality."""
    
    @pytest.fixture
    def settings(self):
        return Settings()
    
    @pytest.fixture
    def state_machine(self, settings):
        return StateMachine(settings)
    
    def test_initial_state(self, state_machine):
        """Test initial state is IDLE."""
        assert state_machine.current_state == TradingState.IDLE
        assert state_machine.previous_state is None
        assert state_machine.retry_count == 0
    
    def test_valid_transitions(self, state_machine):
        """Test valid state transitions."""
        # Test valid transitions from IDLE
        assert state_machine.can_transition_to(TradingState.INITIALIZING) is True
        assert state_machine.can_transition_to(TradingState.ERROR) is True
        assert state_machine.can_transition_to(TradingState.CRITICAL_ERROR) is True
        
        # Test invalid transition
        assert state_machine.can_transition_to(TradingState.BUYING) is False
    
    @pytest.mark.asyncio
    async def test_successful_transition(self, state_machine):
        """Test successful state transition."""
        result = await state_machine.transition_to(TradingState.INITIALIZING)
        
        assert result is True
        assert state_machine.current_state == TradingState.INITIALIZING
        assert state_machine.previous_state == TradingState.IDLE
        assert len(state_machine.state_history) == 1
    
    @pytest.mark.asyncio
    async def test_invalid_transition_raises_error(self, state_machine):
        """Test invalid transition raises StateTransitionError."""
        with pytest.raises(StateTransitionError):
            await state_machine.transition_to(TradingState.BUYING)
    
    @pytest.mark.asyncio
    async def test_error_handling(self, state_machine):
        """Test error handling mechanism."""
        # Transition to a non-error state first
        await state_machine.transition_to(TradingState.INITIALIZING)
        
        # Simulate error
        test_error = Exception("Test error")
        result = await state_machine.handle_error(test_error, "test context")
        
        assert result is True
        assert state_machine.current_state == TradingState.ERROR
        assert state_machine.retry_count == 1
    
    @pytest.mark.asyncio
    async def test_max_retries_critical_error(self, state_machine):
        """Test transition to critical error after max retries."""
        # Transition to a non-error state first
        await state_machine.transition_to(TradingState.INITIALIZING)
        
        # Set retry count to max after transition
        state_machine.retry_count = state_machine.max_retries
        
        # Trigger error that will exceed max retries
        test_error = Exception("Critical test error")
        result = await state_machine.handle_error(test_error, "critical test")
        
        assert result is False
        assert state_machine.current_state == TradingState.CRITICAL_ERROR
    
    def test_wait_conditions(self, state_machine):
        """Test wait condition functionality."""
        # Initially no wait condition
        assert state_machine.is_waiting() is False
        assert state_machine.get_wait_remaining() == 0
        
        # Set wait condition
        state_machine.set_wait_condition(60, "test wait")
        assert state_machine.is_waiting() is True
        assert state_machine.get_wait_remaining() > 0
    
    def test_state_statistics(self, state_machine):
        """Test state statistics generation."""
        # Initially empty statistics
        stats = state_machine.get_state_statistics()
        assert stats == {}
        
        # Add some state history manually for testing
        state_machine.state_history = [
            {
                'timestamp': datetime.utcnow().isoformat(),
                'from_state': 'idle',
                'to_state': 'initializing',
                'duration_seconds': 10.0,
                'context': {},
                'retry_count': 0
            }
        ]
        
        stats = state_machine.get_state_statistics()
        assert 'total_transitions' in stats
        assert 'state_statistics' in stats


class TestPageNavigator:
    """Test page navigator functionality."""
    
    @pytest.fixture
    def settings(self):
        return Settings()
    
    @pytest.fixture
    def mock_browser_manager(self):
        """Create a mock browser manager."""
        mock_browser = Mock(spec=BrowserManager)
        mock_browser.initialize = AsyncMock(return_value=True)
        mock_browser.page = Mock()
        return mock_browser
    
    @pytest.fixture
    def page_navigator(self, mock_browser_manager, settings):
        return PageNavigator(mock_browser_manager, settings)
    
    @pytest.mark.asyncio
    async def test_initialization(self, page_navigator, mock_browser_manager):
        """Test page navigator initialization."""
        result = await page_navigator.initialize()
        
        assert result is True
        mock_browser_manager.initialize.assert_called_once()
        assert page_navigator.page is not None
    
    @pytest.mark.asyncio
    async def test_navigate_to_url_success(self, page_navigator):
        """Test successful URL navigation."""
        # Mock page object
        mock_page = Mock()
        mock_response = Mock()
        mock_response.ok = True
        mock_page.goto = AsyncMock(return_value=mock_response)
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()
        mock_page.url = "https://example.com"
        
        page_navigator.page = mock_page
        
        result = await page_navigator.navigate_to_url("https://example.com")
        
        assert result is True
        mock_page.goto.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_navigate_to_url_failure(self, page_navigator):
        """Test URL navigation failure."""
        # Mock page object with failed response
        mock_page = Mock()
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status = 404
        mock_page.goto = AsyncMock(return_value=mock_response)
        
        page_navigator.page = mock_page
        
        result = await page_navigator.navigate_to_url("https://example.com")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_check_login_status(self, page_navigator):
        """Test login status checking."""
        # Mock page object
        mock_page = Mock()
        mock_page.url = "https://fairview.deadfrontier.com/onlinezombiemmo/index.php"
        mock_page.query_selector = AsyncMock(return_value=None)  # No login form
        mock_page.query_selector_all = AsyncMock(return_value=[])
        
        page_navigator.page = mock_page
        
        result = await page_navigator.check_login_status()
        
        # Should return True for fairview domain
        assert result is True
    
    def test_extract_number_from_text(self, page_navigator):
        """Test number extraction from text."""
        test_cases = [
            ("$1,000", 1000),
            ("Cash: $500", 500),
            ("Level 25", 25),
            ("No numbers", None),
            ("", None)
        ]
        
        for text, expected in test_cases:
            result = page_navigator._extract_number_from_text(text)
            assert result == expected


class TestDatabaseManager:
    """Test database manager functionality."""
    
    @pytest.fixture
    def settings(self):
        # Use in-memory SQLite for testing
        settings = Settings()
        settings.database.url = "sqlite:///:memory:"
        return settings
    
    @pytest.fixture
    async def db_manager(self, settings):
        """Create and initialize database manager for testing."""
        db_manager = DatabaseManager(settings)
        await db_manager.initialize()
        yield db_manager
        await db_manager.close()
    
    @pytest.mark.asyncio
    async def test_initialization(self, settings):
        """Test database manager initialization."""
        db_manager = DatabaseManager(settings)
        result = await db_manager.initialize()
        
        assert result is True
        assert db_manager._initialized is True
        
        await db_manager.close()
    
    @pytest.mark.asyncio
    async def test_create_trading_session(self, db_manager):
        """Test creating a trading session."""
        session = await db_manager.create_trading_session(initial_cash=10000)
        
        assert session is not None
        assert session.initial_cash == 10000
        assert session.state == "idle"
        assert session.id is not None
    
    @pytest.mark.asyncio
    async def test_record_trade(self, db_manager):
        """Test recording a trade."""
        # Create a trading session first
        session = await db_manager.create_trading_session()
        
        trade_data = {
            "session_id": session.id,
            "item_name": "Test Item",
            "buy_price": 100.0,
            "sell_price": 120.0,
            "quantity": 1,
            "profit": 20.0,
            "trade_type": "buy",
            "price_per_unit": 100.0,
            "total_amount": 100.0
        }
        
        result = await db_manager.record_trade(trade_data)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_get_trading_statistics(self, db_manager):
        """Test getting trading statistics."""
        # Create session and record some trades
        session = await db_manager.create_trading_session()
        
        for i in range(3):
            trade_data = {
                "session_id": session.id,
                "item_name": f"Item {i}",
                "buy_price": 100.0,
                "sell_price": 110.0,
                "quantity": 1,
                "profit": 10.0,
                "trade_type": "buy",
                "price_per_unit": 100.0,
                "total_amount": 100.0
            }
            await db_manager.record_trade(trade_data)
        
        stats = await db_manager.get_trading_statistics(session.id)
        
        assert stats["total_trades"] == 3
        assert stats["total_profit"] == 30.0
        assert stats["average_profit"] == 10.0


class TestBrowserManagerEnhancements:
    """Test browser manager enhancements."""
    
    @pytest.fixture
    def settings(self):
        return Settings()
    
    @pytest.fixture
    def browser_manager(self, settings):
        return BrowserManager(settings)
    
    def test_initialization_properties(self, browser_manager):
        """Test enhanced initialization properties."""
        assert browser_manager._initialized is False
        assert browser_manager._error_count == 0
        assert browser_manager._max_errors == 5
        assert browser_manager._network_errors == []
    
    def test_error_count_tracking(self, browser_manager):
        """Test error count tracking."""
        # Simulate console error
        mock_msg = Mock()
        mock_msg.type = "error"
        mock_msg.text = "Test error"
        
        browser_manager._handle_console_message(mock_msg)
        
        assert browser_manager._error_count == 1
    
    def test_network_error_tracking(self, browser_manager):
        """Test network error tracking."""
        mock_request = Mock()
        mock_request.url = "https://example.com"
        mock_request.method = "GET"
        mock_request.failure = "Connection failed"
        
        browser_manager._handle_network_error(mock_request)
        
        assert len(browser_manager._network_errors) == 1
        assert browser_manager._network_errors[0]["url"] == "https://example.com"
    
    def test_page_crash_handling(self, browser_manager):
        """Test page crash handling."""
        browser_manager._handle_page_crash()
        
        # Should set error count to max to force reinitialization
        assert browser_manager._error_count == browser_manager._max_errors
    
    def test_performance_metrics(self, browser_manager):
        """Test performance metrics collection."""
        metrics = browser_manager.get_performance_metrics()
        
        assert "initialized" in metrics
        assert "error_count" in metrics
        assert "network_errors" in metrics
        assert "is_logged_in" in metrics


class TestDataModels:
    """Test data model functionality."""
    
    def test_inventory_status_properties(self):
        """Test inventory status calculated properties."""
        inventory = InventoryStatus(
            current_count=8,
            max_capacity=10,
            items=["item1", "item2"]
        )
        
        assert inventory.is_full is False
        assert inventory.available_space == 2
        assert inventory.utilization_rate == 0.8
    
    def test_inventory_status_full(self):
        """Test inventory status when full."""
        inventory = InventoryStatus(
            current_count=10,
            max_capacity=10,
            items=[]
        )
        
        assert inventory.is_full is True
        assert inventory.available_space == 0
        assert inventory.utilization_rate == 1.0
    
    def test_selling_slots_status(self):
        """Test selling slots status."""
        slots = SellingSlotsStatus(
            current_listings=6,
            max_slots=30,
            listed_items=["item1", "item2"]
        )
        
        assert slots.is_full is False
        assert slots.available_slots == 24
    
    def test_player_resources_trading_capability(self):
        """Test player resources trading capability assessment."""
        # Create component statuses
        inventory = InventoryStatus(current_count=5, max_capacity=10)
        storage = StorageStatus(current_count=20, max_capacity=50)
        selling = SellingSlotsStatus(current_listings=10, max_slots=30)
        
        # Test with money and space - can trade
        resources = PlayerResources(
            cash_on_hand=5000,
            bank_balance=10000,
            inventory_status=inventory,
            storage_status=storage,
            selling_slots_status=selling
        )
        
        assert resources.can_trade is True
        assert resources.total_available_cash == 15000
        assert resources.is_completely_blocked is False
    
    def test_player_resources_blocked_state(self):
        """Test player resources completely blocked state."""
        # Create full statuses
        inventory = InventoryStatus(current_count=10, max_capacity=10)
        storage = StorageStatus(current_count=50, max_capacity=50)
        selling = SellingSlotsStatus(current_listings=30, max_slots=30)
        
        # Test with no money and no space - completely blocked
        resources = PlayerResources(
            cash_on_hand=0,
            bank_balance=0,
            inventory_status=inventory,
            storage_status=storage,
            selling_slots_status=selling
        )
        
        assert resources.can_trade is False
        assert resources.total_available_cash == 0
        assert resources.is_completely_blocked is True


@pytest.mark.asyncio
async def test_integration_state_machine_with_database():
    """Integration test: state machine with database persistence."""
    settings = Settings()
    settings.database.url = "sqlite:///:memory:"
    
    # Initialize components
    db_manager = DatabaseManager(settings)
    await db_manager.initialize()
    
    state_machine = StateMachine(settings)
    
    # Create trading session
    session = await db_manager.create_trading_session()
    
    # Transition states and save to database
    await state_machine.transition_to(TradingState.INITIALIZING)
    
    state_data = {
        "current_state": state_machine.current_state.value,
        "session_id": session.id,
        "state_data": state_machine.export_state_history()
    }
    
    result = await db_manager.save_system_state(state_data)
    assert result is True
    
    # Verify data was saved
    latest_state = await db_manager.get_latest_system_state()
    assert latest_state is not None
    assert latest_state.current_state == TradingState.INITIALIZING.value
    
    await db_manager.close()


if __name__ == "__main__":
    # Run specific test for debugging
    pytest.main([__file__, "-v"]) 