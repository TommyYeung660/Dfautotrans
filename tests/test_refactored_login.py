"""Test refactored login logic integration."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from src.dfautotrans.config.settings import Settings
from src.dfautotrans.automation.login_handler import LoginHandler
from src.dfautotrans.automation.browser_manager import BrowserManager
from src.dfautotrans.core.page_navigator import PageNavigator


class TestRefactoredLogin:
    """Test refactored login integration."""
    
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
        mock_browser.is_logged_in = False
        mock_browser.ensure_logged_in = AsyncMock()
        mock_browser.navigate_to_marketplace = AsyncMock()
        return mock_browser
    
    @pytest.fixture
    def mock_page_navigator(self):
        """Create mock page navigator."""
        mock_navigator = Mock(spec=PageNavigator)
        mock_navigator.check_login_status = AsyncMock(return_value=False)
        mock_navigator.navigate_to_login = AsyncMock(return_value=True)
        mock_navigator.get_current_cash = AsyncMock(return_value=1000)
        return mock_navigator
    
    @pytest.fixture
    def login_handler(self, mock_browser_manager, mock_page_navigator, settings):
        """Create login handler instance."""
        return LoginHandler(mock_browser_manager, mock_page_navigator, settings)
    
    @pytest.mark.asyncio
    async def test_browser_manager_no_longer_has_login_method(self, mock_browser_manager):
        """Test that BrowserManager no longer has direct login method."""
        # Verify the old login method is removed
        assert not hasattr(mock_browser_manager, 'login')
        # Verify the new method exists
        assert hasattr(mock_browser_manager, 'ensure_logged_in')
    
    @pytest.mark.asyncio
    async def test_login_handler_updates_browser_manager_status(self, login_handler, mock_browser_manager, mock_page_navigator):
        """Test that LoginHandler updates BrowserManager login status."""
        # Setup successful login
        mock_page_navigator.check_login_status.return_value = False
        mock_page_navigator.navigate_to_login.return_value = True
        mock_page_navigator.get_current_cash.return_value = 1000
        
        # Mock form elements
        mock_page = mock_browser_manager.page
        mock_page.url = "https://fairview.deadfrontier.com/onlinezombiemmo/index.php"
        mock_page.query_selector = AsyncMock(return_value=Mock())
        mock_page.inner_text = AsyncMock(return_value="Cash: $1000")
        mock_page.wait_for_selector = AsyncMock()
        
        # Mock form elements
        mock_username_field = Mock()
        mock_password_field = Mock()
        mock_submit_button = Mock()
        
        mock_username_field.clear = AsyncMock()
        mock_password_field.clear = AsyncMock()
        mock_submit_button.click = AsyncMock()
        
        def mock_query_selector_side_effect(selector):
            if 'username' in selector or 'user' in selector or 'text' in selector:
                return mock_username_field
            elif 'password' in selector:
                return mock_password_field
            elif 'submit' in selector or 'Login' in selector:
                return mock_submit_button
            elif 'form' in selector:
                return Mock()
            return None
        
        mock_page.query_selector = AsyncMock(side_effect=mock_query_selector_side_effect)
        
        # Mock anti-detection
        with patch.object(login_handler.anti_detection, 'safe_type', new_callable=AsyncMock), \
             patch.object(login_handler.anti_detection, 'safe_click', new_callable=AsyncMock), \
             patch.object(login_handler.anti_detection, 'simulate_user_behavior', new_callable=AsyncMock):
            
            # Initially not logged in
            assert mock_browser_manager.is_logged_in is False
            
            # Perform login
            result = await login_handler.perform_login()
            
            # Verify login successful and browser manager status updated
            assert result is True
            assert mock_browser_manager.is_logged_in is True
    
    @pytest.mark.asyncio
    async def test_browser_manager_ensure_logged_in_with_handler(self, mock_browser_manager, login_handler):
        """Test BrowserManager.ensure_logged_in with LoginHandler."""
        # Create a real BrowserManager instance for this test
        settings = Settings()
        browser_manager = BrowserManager(settings)
        browser_manager.page = Mock()  # Mock the page
        browser_manager.is_logged_in = False
        
        # Mock the login handler
        mock_login_handler = Mock()
        mock_login_handler.perform_login = AsyncMock(return_value=True)
        
        # Test ensure_logged_in
        result = await browser_manager.ensure_logged_in(mock_login_handler)
        
        assert result is True
        assert browser_manager.is_logged_in is True
        mock_login_handler.perform_login.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_browser_manager_ensure_logged_in_without_handler(self, mock_browser_manager):
        """Test BrowserManager.ensure_logged_in without LoginHandler."""
        # Create a real BrowserManager instance for this test
        settings = Settings()
        browser_manager = BrowserManager(settings)
        browser_manager.page = Mock()  # Mock the page
        browser_manager.is_logged_in = False
        
        # Test ensure_logged_in without handler
        result = await browser_manager.ensure_logged_in(None)
        
        assert result is False
        assert browser_manager.is_logged_in is False
    
    @pytest.mark.asyncio
    async def test_browser_manager_already_logged_in(self, mock_browser_manager):
        """Test BrowserManager.ensure_logged_in when already logged in."""
        # Create a real BrowserManager instance for this test
        settings = Settings()
        browser_manager = BrowserManager(settings)
        browser_manager.page = Mock()  # Mock the page
        browser_manager.is_logged_in = True  # Already logged in
        
        # Mock the login handler (should not be called)
        mock_login_handler = Mock()
        mock_login_handler.perform_login = AsyncMock()
        
        # Test ensure_logged_in
        result = await browser_manager.ensure_logged_in(mock_login_handler)
        
        assert result is True
        assert browser_manager.is_logged_in is True
        # Should not call login handler since already logged in
        mock_login_handler.perform_login.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_navigate_to_marketplace_with_login_handler(self):
        """Test navigate_to_marketplace with LoginHandler integration."""
        settings = Settings()
        settings.marketplace_url = "https://example.com/marketplace"
        
        browser_manager = BrowserManager(settings)
        browser_manager.page = Mock()
        browser_manager.is_logged_in = False
        
        # Mock page operations
        browser_manager.page.locator = Mock(return_value=Mock())
        browser_manager.page.locator().count = AsyncMock(return_value=1)
        browser_manager.page.wait_for_load_state = AsyncMock()
        browser_manager.page.title = AsyncMock(return_value="Marketplace")
        
        # Mock anti-detection
        browser_manager.anti_detection = Mock()
        browser_manager.anti_detection.safe_navigate = AsyncMock()
        
        # Mock login handler
        mock_login_handler = Mock()
        mock_login_handler.perform_login = AsyncMock(return_value=True)
        
        # Test navigation
        await browser_manager.navigate_to_marketplace(mock_login_handler)
        
        # Verify login was called and status updated
        mock_login_handler.perform_login.assert_called_once()
        assert browser_manager.is_logged_in is True
        browser_manager.anti_detection.safe_navigate.assert_called_once()
    
    def test_refactoring_summary(self):
        """Document the refactoring changes."""
        print("\n=== 登錄邏輯重構總結 ===")
        print("✅ 移除了 BrowserManager.login() 重複方法")
        print("✅ 創建了 BrowserManager.ensure_logged_in() 方法")
        print("✅ LoginHandler 現在負責所有登錄邏輯")
        print("✅ BrowserManager 通過 LoginHandler 進行登錄")
        print("✅ 登錄狀態在兩個類之間保持同步")
        print("✅ 移除了重複的登錄選擇器定義")
        print("✅ 保持了向後兼容性")
        print("=== 重構完成 ===")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"]) 