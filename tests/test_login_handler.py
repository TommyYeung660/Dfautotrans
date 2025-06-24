"""Tests for Login Handler module."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.dfautotrans.config.settings import Settings
from src.dfautotrans.automation.login_handler import LoginHandler, LoginError
from src.dfautotrans.automation.browser_manager import BrowserManager
from src.dfautotrans.core.page_navigator import PageNavigator


class TestLoginHandler:
    """Test login handler functionality."""
    
    @pytest.fixture
    def settings(self):
        """Create test settings."""
        settings = Settings()
        settings.username = "test_user"
        settings.password = "test_password"
        return settings
    
    @pytest.fixture
    def mock_browser_manager(self):
        """Create mock browser manager."""
        mock_browser = Mock(spec=BrowserManager)
        mock_browser.page = Mock()
        return mock_browser
    
    @pytest.fixture
    def mock_page_navigator(self):
        """Create mock page navigator."""
        mock_navigator = Mock(spec=PageNavigator)
        mock_navigator.check_login_status = AsyncMock(return_value=False)
        mock_navigator.navigate_to_login = AsyncMock(return_value=True)
        mock_navigator.get_current_cash = AsyncMock(return_value=None)
        return mock_navigator
    
    @pytest.fixture
    def login_handler(self, mock_browser_manager, mock_page_navigator, settings):
        """Create login handler instance."""
        return LoginHandler(mock_browser_manager, mock_page_navigator, settings)
    
    def test_initialization(self, login_handler):
        """Test login handler initialization."""
        assert login_handler._login_attempts == 0
        assert login_handler._max_login_attempts == 3
        assert login_handler._last_login_time is None
        assert login_handler._login_cooldown == 30
    
    @pytest.mark.asyncio
    async def test_check_login_status_not_logged_in(self, login_handler, mock_page_navigator):
        """Test login status check when not logged in."""
        mock_page_navigator.check_login_status.return_value = False
        
        result = await login_handler.check_login_status()
        
        assert result is False
        mock_page_navigator.check_login_status.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_check_login_status_already_logged_in(self, login_handler, mock_page_navigator):
        """Test login status check when already logged in."""
        mock_page_navigator.check_login_status.return_value = True
        
        result = await login_handler.check_login_status()
        
        assert result is True
        mock_page_navigator.check_login_status.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_perform_login_already_logged_in(self, login_handler, mock_page_navigator):
        """Test login when already logged in."""
        mock_page_navigator.check_login_status.return_value = True
        
        result = await login_handler.perform_login()
        
        assert result is True
        # Should not attempt navigation if already logged in
        mock_page_navigator.navigate_to_login.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_perform_login_no_credentials(self, mock_browser_manager, mock_page_navigator):
        """Test login without credentials."""
        settings = Settings()
        # Override username and password to be empty
        settings.username = ""
        settings.password = ""
        login_handler = LoginHandler(mock_browser_manager, mock_page_navigator, settings)
        
        with pytest.raises(LoginError, match="Login credentials not configured"):
            await login_handler.perform_login()
    
    @pytest.mark.asyncio
    async def test_perform_login_navigation_failure(self, login_handler, mock_page_navigator):
        """Test login when navigation fails."""
        mock_page_navigator.check_login_status.return_value = False
        mock_page_navigator.navigate_to_login.return_value = False
        
        result = await login_handler.perform_login()
        
        assert result is False
        assert login_handler._login_attempts == 1
    
    @pytest.mark.asyncio
    async def test_perform_login_success_flow(self, login_handler, mock_page_navigator, mock_browser_manager):
        """Test successful login flow."""
        # Setup mocks
        mock_page_navigator.check_login_status.return_value = False
        mock_page_navigator.navigate_to_login.return_value = True
        
        # Mock page elements
        mock_page = mock_browser_manager.page
        mock_username_field = Mock()
        mock_password_field = Mock()
        mock_submit_button = Mock()
        
        mock_username_field.clear = AsyncMock()
        mock_password_field.clear = AsyncMock()
        mock_submit_button.click = AsyncMock()
        
        # Setup query_selector responses - return the actual mock objects, not AsyncMock
        def mock_query_selector(selector):
            if 'username' in selector or 'user' in selector or 'text' in selector:
                return mock_username_field
            elif 'password' in selector:
                return mock_password_field
            elif 'submit' in selector or 'Login' in selector:
                return mock_submit_button
            elif 'form' in selector:
                return Mock()
            elif 'error' in selector or 'captcha' in selector:
                return None
            return None
        
        mock_page.query_selector = AsyncMock(side_effect=mock_query_selector)
        mock_page.wait_for_selector = AsyncMock()
        mock_page.url = "https://fairview.deadfrontier.com/test"
        mock_page.inner_text = AsyncMock(return_value="Cash: $1000")
        
        # Mock anti-detection
        with patch.object(login_handler.anti_detection, 'safe_type', new_callable=AsyncMock) as mock_type, \
             patch.object(login_handler.anti_detection, 'safe_click', new_callable=AsyncMock) as mock_click, \
             patch.object(login_handler.anti_detection, 'simulate_user_behavior', new_callable=AsyncMock):
            
            result = await login_handler.perform_login()
        
        assert result is True
        assert login_handler._login_attempts == 0  # Should be reset on success
        mock_type.assert_called()  # Should have typed username and password
        mock_click.assert_called()  # Should have clicked submit button
    
    @pytest.mark.asyncio
    async def test_verify_login_success_by_url(self, login_handler, mock_browser_manager):
        """Test login verification by URL."""
        mock_page = mock_browser_manager.page
        mock_page.url = "https://fairview.deadfrontier.com/onlinezombiemmo/index.php"
        mock_page.query_selector = AsyncMock(return_value=None)
        mock_page.inner_text = AsyncMock(return_value="")
        
        result = await login_handler.verify_login_success()
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_verify_login_success_by_element(self, login_handler, mock_browser_manager):
        """Test login verification by element presence."""
        mock_page = mock_browser_manager.page
        mock_page.url = "https://example.com"
        
        # Mock logout element found
        def mock_query_selector(selector):
            if '.logout' in selector:
                return Mock()
            return None
        
        mock_page.query_selector = AsyncMock(side_effect=mock_query_selector)
        mock_page.inner_text = AsyncMock(return_value="")
        
        result = await login_handler.verify_login_success()
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_verify_login_success_by_cash(self, login_handler, mock_page_navigator, mock_browser_manager):
        """Test login verification by cash detection."""
        mock_page = mock_browser_manager.page
        mock_page.url = "https://example.com"
        mock_page.query_selector = AsyncMock(return_value=None)
        mock_page.inner_text = AsyncMock(return_value="")
        
        # Mock cash detection
        mock_page_navigator.get_current_cash.return_value = 5000
        
        result = await login_handler.verify_login_success()
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_verify_login_failure(self, login_handler, mock_browser_manager, mock_page_navigator):
        """Test login verification failure."""
        mock_page = mock_browser_manager.page
        mock_page.url = "https://example.com"
        mock_page.query_selector = AsyncMock(return_value=None)
        mock_page.inner_text = AsyncMock(return_value="")
        mock_page_navigator.get_current_cash.return_value = None
        
        result = await login_handler.verify_login_success()
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_logout_success(self, login_handler, mock_browser_manager, mock_page_navigator):
        """Test successful logout."""
        mock_page = mock_browser_manager.page
        mock_logout_element = Mock()
        mock_logout_element.click = AsyncMock()
        
        def mock_query_selector(selector):
            if 'logout' in selector:
                return mock_logout_element
            return None
        
        mock_page.query_selector = AsyncMock(side_effect=mock_query_selector)
        
        # Mock logout verification
        mock_page_navigator.check_login_status.return_value = False
        
        with patch.object(login_handler.anti_detection, 'safe_click', new_callable=AsyncMock) as mock_click:
            result = await login_handler.logout()
        
        assert result is True
        mock_click.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_logout_no_logout_link(self, login_handler, mock_browser_manager):
        """Test logout when no logout link found."""
        mock_page = mock_browser_manager.page
        mock_page.query_selector = AsyncMock(return_value=None)
        
        result = await login_handler.logout()
        
        assert result is False
    
    def test_can_attempt_login_max_attempts(self, login_handler):
        """Test login attempt limitation."""
        login_handler._login_attempts = login_handler._max_login_attempts
        
        result = login_handler._can_attempt_login()
        
        assert result is False
    
    def test_can_attempt_login_cooldown(self, login_handler):
        """Test login cooldown."""
        login_handler._last_login_time = asyncio.get_event_loop().time() - 10  # 10 seconds ago
        login_handler._login_cooldown = 30  # 30 second cooldown
        
        result = login_handler._can_attempt_login()
        
        assert result is False
    
    def test_can_attempt_login_allowed(self, login_handler):
        """Test login attempt allowed."""
        result = login_handler._can_attempt_login()
        
        assert result is True
    
    def test_reset_login_attempts(self, login_handler):
        """Test login attempt reset."""
        login_handler._login_attempts = 2
        
        login_handler._reset_login_attempts()
        
        assert login_handler._login_attempts == 0
        assert login_handler._last_login_time is not None
    
    @pytest.mark.asyncio
    async def test_handle_login_dialog_found(self, login_handler, mock_browser_manager):
        """Test handling login dialog when found."""
        mock_page = mock_browser_manager.page
        mock_dialog = Mock()
        mock_form = Mock()
        
        # Mock form elements
        mock_username = Mock()
        mock_password = Mock()
        mock_submit = Mock()
        mock_username.fill = AsyncMock()
        mock_password.fill = AsyncMock()
        mock_submit.click = AsyncMock()
        
        mock_form.query_selector = AsyncMock(side_effect=[mock_username, mock_password, mock_submit])
        mock_dialog.query_selector = AsyncMock(return_value=mock_form)
        
        def mock_query_selector(selector):
            if '.modal' in selector:
                return mock_dialog
            return None
        
        mock_page.query_selector = AsyncMock(side_effect=mock_query_selector)
        
        result = await login_handler.handle_login_dialog()
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_handle_login_dialog_not_found(self, login_handler, mock_browser_manager):
        """Test handling login dialog when not found."""
        mock_page = mock_browser_manager.page
        mock_page.query_selector = AsyncMock(return_value=None)
        
        result = await login_handler.handle_login_dialog()
        
        assert result is False
    
    def test_get_login_status(self, login_handler):
        """Test getting login status."""
        login_handler._login_attempts = 1
        login_handler._last_login_time = asyncio.get_event_loop().time() - 5
        
        status = login_handler.get_login_status()
        
        assert status['login_attempts'] == 1
        assert status['max_attempts'] == 3
        assert status['last_login_time'] is not None
        assert 'cooldown_remaining' in status
        assert 'can_attempt_login' in status
    
    def test_reset_login_state(self, login_handler):
        """Test resetting login state."""
        login_handler._login_attempts = 2
        login_handler._last_login_time = asyncio.get_event_loop().time()
        
        login_handler.reset_login_state()
        
        assert login_handler._login_attempts == 0
        assert login_handler._last_login_time is None


@pytest.mark.asyncio
async def test_integration_login_with_page_navigator():
    """Integration test: login handler with page navigator."""
    settings = Settings()
    settings.username = "test_user"
    settings.password = "test_password"
    
    # Create mock components
    mock_browser = Mock(spec=BrowserManager)
    mock_browser.page = Mock()
    mock_browser.page.url = "https://fairview.deadfrontier.com/test"
    mock_browser.page.query_selector = AsyncMock(return_value=None)
    mock_browser.page.inner_text = AsyncMock(return_value="Cash: $1000")
    
    mock_navigator = Mock(spec=PageNavigator)
    mock_navigator.check_login_status = AsyncMock(return_value=True)
    mock_navigator.get_current_cash = AsyncMock(return_value=1000)
    
    # Create login handler
    login_handler = LoginHandler(mock_browser, mock_navigator, settings)
    
    # Test login check
    result = await login_handler.check_login_status()
    assert result is True
    
    # Test login verification
    verify_result = await login_handler.verify_login_success()
    assert verify_result is True


if __name__ == "__main__":
    # Run specific test for debugging
    pytest.main([__file__, "-v"]) 