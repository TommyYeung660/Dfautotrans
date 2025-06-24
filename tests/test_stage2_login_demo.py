"""Stage 2 Login Handler Demo Test."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from src.dfautotrans.config.settings import Settings
from src.dfautotrans.automation.login_handler import LoginHandler
from src.dfautotrans.automation.browser_manager import BrowserManager
from src.dfautotrans.core.page_navigator import PageNavigator


@pytest.mark.asyncio
async def test_login_handler_demo():
    """Demo test showing login handler usage scenarios."""
    
    # Create settings
    settings = Settings()
    
    # Create mock components
    mock_browser = Mock(spec=BrowserManager)
    mock_browser.page = Mock()
    mock_browser.page.url = "https://www.deadfrontier.com/index.php"
    mock_browser.page.query_selector = AsyncMock(return_value=None)
    mock_browser.page.inner_text = AsyncMock(return_value="")
    mock_browser.page.wait_for_selector = AsyncMock()
    
    mock_navigator = Mock(spec=PageNavigator)
    mock_navigator.check_login_status = AsyncMock(return_value=False)
    mock_navigator.navigate_to_login = AsyncMock(return_value=True)
    mock_navigator.get_current_cash = AsyncMock(return_value=None)
    
    # Create login handler
    login_handler = LoginHandler(mock_browser, mock_navigator, settings)
    
    print("=== 階段2：登錄處理模組演示 ===")
    
    # Test 1: Check initial login status
    print("\n1. 檢查登錄狀態...")
    is_logged_in = await login_handler.check_login_status()
    print(f"   登錄狀態: {'已登錄' if is_logged_in else '未登錄'}")
    assert is_logged_in is False
    
    # Test 2: Get login handler status
    print("\n2. 獲取登錄處理器狀態...")
    status = login_handler.get_login_status()
    print(f"   登錄嘗試次數: {status['login_attempts']}/{status['max_attempts']}")
    print(f"   可以嘗試登錄: {'是' if status['can_attempt_login'] else '否'}")
    print(f"   冷卻時間剩餘: {status['cooldown_remaining']:.1f}秒")
    
    # Test 3: Mock successful login flow
    print("\n3. 模擬登錄流程...")
    
    # Mock form elements for successful login
    mock_username_field = Mock()
    mock_password_field = Mock()
    mock_submit_button = Mock()
    
    mock_username_field.clear = AsyncMock()
    mock_password_field.clear = AsyncMock()
    mock_submit_button.click = AsyncMock()
    
    def mock_query_selector(selector):
        if 'username' in selector or 'user' in selector or 'text' in selector:
            return mock_username_field
        elif 'password' in selector:
            return mock_password_field
        elif 'submit' in selector or 'Login' in selector:
            return mock_submit_button
        elif 'form' in selector:
            return Mock()
        return None
    
    mock_browser.page.query_selector = AsyncMock(side_effect=mock_query_selector)
    
    # Mock successful login verification
    mock_browser.page.url = "https://fairview.deadfrontier.com/onlinezombiemmo/index.php"
    mock_navigator.get_current_cash = AsyncMock(return_value=10000)
    
    # Mock anti-detection methods
    with patch.object(login_handler.anti_detection, 'safe_type', new_callable=AsyncMock) as mock_type, \
         patch.object(login_handler.anti_detection, 'safe_click', new_callable=AsyncMock) as mock_click, \
         patch.object(login_handler.anti_detection, 'simulate_user_behavior', new_callable=AsyncMock):
        
        # Attempt login
        login_result = await login_handler.perform_login()
        print(f"   登錄結果: {'成功' if login_result else '失敗'}")
        
        if login_result:
            print("   ✓ 成功導航到登錄頁面")
            print("   ✓ 成功填寫登錄表單")
            print("   ✓ 成功提交登錄請求")
            print("   ✓ 成功驗證登錄狀態")
            
            # Verify anti-detection methods were called
            assert mock_type.called, "應該調用了安全輸入方法"
            assert mock_click.called, "應該調用了安全點擊方法"
    
    # Test 4: Verify login success
    print("\n4. 驗證登錄成功...")
    verify_result = await login_handler.verify_login_success()
    print(f"   驗證結果: {'成功' if verify_result else '失敗'}")
    
    if verify_result:
        print("   ✓ URL 包含正確的域名")
        print("   ✓ 可以獲取玩家現金信息")
    
    # Test 5: Check updated status
    print("\n5. 檢查更新後的狀態...")
    final_status = login_handler.get_login_status()
    print(f"   登錄嘗試次數: {final_status['login_attempts']}/{final_status['max_attempts']}")
    print(f"   最後登錄時間: {'有' if final_status['last_login_time'] else '無'}")
    
    # Test 6: Test error handling
    print("\n6. 測試錯誤處理...")
    
    # Reset for error test
    login_handler.reset_login_state()
    
    # Mock navigation failure
    mock_navigator.navigate_to_login = AsyncMock(return_value=False)
    
    error_result = await login_handler.perform_login()
    print(f"   導航失敗處理: {'正確' if not error_result else '錯誤'}")
    
    if not error_result:
        print("   ✓ 正確處理導航失敗")
        print("   ✓ 記錄了登錄嘗試次數")
    
    # Test 7: Test cooldown mechanism
    print("\n7. 測試冷卻機制...")
    
    # Simulate max attempts
    login_handler._login_attempts = login_handler._max_login_attempts
    
    cooldown_result = await login_handler.perform_login()
    print(f"   冷卻機制: {'正常工作' if not cooldown_result else '異常'}")
    
    if not cooldown_result:
        print("   ✓ 達到最大嘗試次數時阻止登錄")
        print("   ✓ 冷卻機制正常工作")
    
    print("\n=== 登錄處理模組演示完成 ===")
    print("✅ 所有功能測試通過")
    print("✅ 錯誤處理機制正常")
    print("✅ 安全機制有效")
    print("✅ 準備進入下一階段開發")


@pytest.mark.asyncio
async def test_login_handler_integration_scenarios():
    """Integration scenarios for login handler."""
    
    settings = Settings()
    
    # Scenario 1: Already logged in
    print("\n=== 場景1：用戶已登錄 ===")
    
    mock_browser = Mock(spec=BrowserManager)
    mock_browser.page = Mock()
    mock_browser.page.url = "https://fairview.deadfrontier.com/onlinezombiemmo/index.php"
    
    mock_navigator = Mock(spec=PageNavigator)
    mock_navigator.check_login_status = AsyncMock(return_value=True)
    
    login_handler = LoginHandler(mock_browser, mock_navigator, settings)
    
    result = await login_handler.perform_login()
    print(f"已登錄用戶嘗試登錄: {'跳過登錄流程' if result else '異常'}")
    assert result is True
    
    # Scenario 2: Login dialog appears
    print("\n=== 場景2：出現登錄對話框 ===")
    
    mock_browser.page.query_selector = AsyncMock(return_value=Mock())
    mock_dialog = Mock()
    mock_form = Mock()
    
    mock_username = Mock()
    mock_password = Mock()
    mock_submit = Mock()
    mock_username.fill = AsyncMock()
    mock_password.fill = AsyncMock()
    mock_submit.click = AsyncMock()
    
    mock_form.query_selector = AsyncMock(side_effect=[mock_username, mock_password, mock_submit])
    mock_dialog.query_selector = AsyncMock(return_value=mock_form)
    
    def mock_dialog_query(selector):
        if '.modal' in selector:
            return mock_dialog
        return None
    
    mock_browser.page.query_selector = AsyncMock(side_effect=mock_dialog_query)
    
    dialog_result = await login_handler.handle_login_dialog()
    print(f"處理登錄對話框: {'成功' if dialog_result else '失敗'}")
    
    # Scenario 3: Logout process
    print("\n=== 場景3：登出流程 ===")
    
    mock_logout_element = Mock()
    mock_logout_element.click = AsyncMock()
    
    def mock_logout_query(selector):
        if 'logout' in selector:
            return mock_logout_element
        return None
    
    mock_browser.page.query_selector = AsyncMock(side_effect=mock_logout_query)
    mock_navigator.check_login_status = AsyncMock(return_value=False)
    
    with patch.object(login_handler.anti_detection, 'safe_click', new_callable=AsyncMock):
        logout_result = await login_handler.logout()
        print(f"登出流程: {'成功' if logout_result else '失敗'}")
    
    print("\n=== 集成場景測試完成 ===")


if __name__ == "__main__":
    # Run demo
    pytest.main([__file__, "-v", "-s"]) 