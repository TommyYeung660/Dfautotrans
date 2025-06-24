"""Login handler for Dead Frontier Auto Trading System."""

import asyncio
import re
from typing import Optional, Dict, Any
from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError
from loguru import logger

from ..config.settings import Settings
from ..core.page_navigator import PageNavigator
from ..automation.browser_manager import BrowserManager
from ..automation.anti_detection import AntiDetectionManager


class LoginError(Exception):
    """Login-related error."""
    pass


class LoginHandler:
    """Handles Dead Frontier login operations."""
    
    def __init__(self, browser_manager: BrowserManager, page_navigator: PageNavigator, settings: Settings):
        self.browser_manager = browser_manager
        self.page_navigator = page_navigator
        self.settings = settings
        self.anti_detection = AntiDetectionManager(settings.anti_detection)
        
        # Login state tracking
        self._login_attempts = 0
        self._max_login_attempts = 3
        self._last_login_time = None
        self._login_cooldown = 30  # seconds
        
        # Login selectors (based on MCP analysis)
        self.selectors = {
            'login_iframe': 'iframe[name*="fancybox-frame"]',
            'login_section': 'table tr:has(button:has-text("Log in"))',
            'username_field': 'table tr:nth-child(1) input[type="text"]',
            'password_field': 'table tr:nth-child(2) input[type="password"]',
            'login_button': 'button:has-text("Log in")',
            'stay_logged_checkbox': 'table tr:nth-child(3) input[type="checkbox"]',
            'create_username_field': 'table:first-of-type input[type="text"]:first-of-type',
            'create_email_field': 'table:first-of-type input[type="text"]:nth-of-type(2)',
            'create_password_field': 'table:first-of-type input[type="password"]:first-of-type',
            'create_confirm_password_field': 'table:first-of-type input[type="password"]:nth-of-type(2)',
            'create_account_button': 'button:has-text("Create Account")'
        }
        
        # Success indicators
        self.success_indicators = {
            'outpost_url': 'fairview.deadfrontier.com/onlinezombiemmo/index.php',
            'user_info': 'generic:has-text("Level")',
            'cash_display': 'generic:has-text("Cash:")',
            'logout_link': 'a[href*="logout"]'
        }
    
    async def check_login_status(self) -> bool:
        """Check if user is currently logged in."""
        try:
            # Use page navigator's login check
            is_logged_in = await self.page_navigator.check_login_status()
            
            if is_logged_in:
                logger.info("User is already logged in")
                return True
            
            logger.info("User is not logged in")
            return False
            
        except Exception as e:
            logger.error(f"Error checking login status: {e}")
            return False
    
    async def perform_login(self) -> bool:
        """執行登錄操作"""
        try:
            logger.info("🔐 開始執行登錄流程...")
            
            # 1. 導航到登錄頁面
            logger.info("1️⃣ 導航到登錄頁面...")
            await self.browser_manager.page.goto(
                "https://www.deadfrontier.com/index.php?autologin=1",
                wait_until="domcontentloaded"
            )
            
            # 2. 等待登錄 iframe 加載
            logger.info("2️⃣ 等待登錄表單加載...")
            await self._wait_for_login_form()
            
            # 3. 填寫登錄信息
            logger.info("3️⃣ 填寫登錄信息...")
            await self._fill_login_credentials()
            
            # 4. 提交登錄表單
            logger.info("4️⃣ 提交登錄表單...")
            await self._submit_login_form()
            
            # 5. 等待登錄結果
            logger.info("5️⃣ 等待登錄結果...")
            success = await self._wait_for_login_result()
            
            if success:
                logger.info("✅ 登錄成功！")
                # 同步狀態到 BrowserManager
                self.browser_manager.is_logged_in = True
                return True
            else:
                logger.error("❌ 登錄失敗")
                self.browser_manager.is_logged_in = False
                return False
                
        except Exception as e:
            logger.error(f"❌ 登錄過程中發生錯誤: {e}")
            self.browser_manager.is_logged_in = False
            return False
    
    async def _wait_for_login_form(self) -> None:
        """等待登錄表單加載"""
        try:
            # 等待 iframe 出現
            await self.browser_manager.page.wait_for_selector(
                self.selectors['login_iframe'],
                timeout=10000
            )
            
            # 獲取 iframe
            iframe_element = await self.browser_manager.page.query_selector(self.selectors['login_iframe'])
            if not iframe_element:
                raise Exception("無法找到登錄 iframe")
            
            iframe = await iframe_element.content_frame()
            if not iframe:
                raise Exception("無法獲取 iframe 內容")
            
            # 等待表單元素加載
            await iframe.wait_for_selector(self.selectors['password_field'], timeout=10000)
            logger.info("✅ 登錄表單加載完成")
            
        except Exception as e:
            logger.error(f"❌ 等待登錄表單失敗: {e}")
            raise
    
    async def _fill_login_credentials(self) -> None:
        """填寫登錄憑證"""
        try:
            # 獲取 iframe
            iframe_element = await self.browser_manager.page.query_selector(self.selectors['login_iframe'])
            iframe = await iframe_element.content_frame()
            
            # 首先找到右邊的登錄區域 - 包含 "Log in" 按鈕的表格
            # 根據快照分析，右邊的登錄區域是第三個 cell
            login_cell = await iframe.query_selector('table tr td:nth-child(3)')
            if not login_cell:
                raise Exception("無法找到登錄區域")
            
            # 在登錄區域內查找用戶名欄位
            username_field = await login_cell.query_selector('input[type="text"]')
            if username_field:
                current_username = await username_field.input_value()
                if not current_username:
                    # 如果沒有預填用戶名，則填入
                    await username_field.fill(self.settings.username)
                    logger.info(f"✅ 已填入用戶名: {self.settings.username}")
                else:
                    logger.info(f"ℹ️ 用戶名已預填: {current_username}")
            else:
                logger.warning("⚠️ 未找到用戶名欄位")
            
            # 在登錄區域內查找密碼欄位
            password_field = await login_cell.query_selector('input[type="password"]')
            if password_field:
                await password_field.fill(self.settings.password)
                logger.info("✅ 已填入密碼")
            else:
                raise Exception("無法找到密碼欄位")
            
            # 可選：勾選"保持登錄"
            stay_logged_checkbox = await login_cell.query_selector('input[type="checkbox"]')
            if stay_logged_checkbox and not await stay_logged_checkbox.is_checked():
                await stay_logged_checkbox.check()
                logger.info("✅ 已勾選保持登錄")
            
        except Exception as e:
            logger.error(f"❌ 填寫登錄憑證失敗: {e}")
            raise
    
    async def _submit_login_form(self) -> None:
        """提交登錄表單"""
        try:
            # 獲取 iframe
            iframe_element = await self.browser_manager.page.query_selector(self.selectors['login_iframe'])
            iframe = await iframe_element.content_frame()
            
            # 找到右邊的登錄區域
            login_cell = await iframe.query_selector('table tr td:nth-child(3)')
            if not login_cell:
                raise Exception("無法找到登錄區域")
            
            # 在登錄區域內查找登錄按鈕
            login_button = await login_cell.query_selector('button')
            if not login_button:
                # 如果找不到按鈕，嘗試查找 input[type="submit"]
                login_button = await login_cell.query_selector('input[type="submit"]')
            
            if login_button:
                await login_button.click()
                logger.info("✅ 已提交登錄表單")
            else:
                # 如果找不到按鈕，嘗試提交表單
                form = await iframe.query_selector('form')
                if form:
                    await form.evaluate("form => form.submit()")
                    logger.info("✅ 已提交登錄表單（通過表單提交）")
                else:
                    raise Exception("無法找到登錄按鈕或表單")
            
        except Exception as e:
            logger.error(f"❌ 提交登錄表單失敗: {e}")
            raise
    
    async def _wait_for_login_result(self) -> bool:
        """等待登錄結果"""
        try:
            # 等待頁面跳轉或錯誤信息
            await asyncio.sleep(2)  # 給頁面一些時間開始跳轉
            
            # 等待最多 15 秒看是否跳轉到遊戲主頁
            for attempt in range(15):
                current_url = self.browser_manager.page.url
                logger.debug(f"檢查登錄結果，當前 URL: {current_url}")
                
                # 檢查是否跳轉到遊戲主頁
                if self.success_indicators['outpost_url'] in current_url:
                    logger.info("✅ 檢測到頁面跳轉到遊戲主頁")
                    
                    # 進一步驗證登錄成功
                    await asyncio.sleep(2)  # 等待頁面完全加載
                    
                    # 檢查是否有用戶信息顯示
                    try:
                        # 檢查現金顯示
                        cash_element = await self.browser_manager.page.query_selector('text=/Cash:/')
                        if cash_element:
                            logger.info("✅ 檢測到現金信息，登錄成功")
                            return True
                        
                        # 檢查用戶等級信息
                        level_element = await self.browser_manager.page.query_selector('text=/Level/')
                        if level_element:
                            logger.info("✅ 檢測到用戶等級信息，登錄成功")
                            return True
                            
                    except Exception as e:
                        logger.debug(f"檢查登錄成功指標時出錯: {e}")
                
                await asyncio.sleep(1)
            
            logger.error("❌ 登錄超時或失敗")
            return False
            
        except Exception as e:
            logger.error(f"❌ 等待登錄結果時發生錯誤: {e}")
            return False
    
    async def handle_login_dialog(self) -> bool:
        """Handle login dialog if it appears."""
        page = self.browser_manager.page
        if not page:
            return False
        
        try:
            # Check for modal dialog or popup
            dialog_selectors = [
                '.modal', '.popup', '.dialog',
                '[role="dialog"]', '[aria-modal="true"]'
            ]
            
            for selector in dialog_selectors:
                dialog = await page.query_selector(selector)
                if dialog:
                    logger.info("Login dialog detected")
                    
                    # Look for login form within dialog
                    form_in_dialog = await dialog.query_selector('form')
                    if form_in_dialog:
                        logger.info("Processing login form in dialog")
                        return await self._process_login_form(form_in_dialog)
            
            return False
            
        except Exception as e:
            logger.error(f"Error handling login dialog: {e}")
            return False
    
    async def verify_login_success(self) -> bool:
        """驗證登錄是否成功"""
        try:
            # 檢查當前 URL
            current_url = self.browser_manager.page.url
            if self.success_indicators['outpost_url'] not in current_url:
                logger.error("❌ 登錄驗證失敗：未跳轉到遊戲主頁")
                return False
            
            # 檢查頁面內容
            try:
                # 等待並檢查現金信息
                cash_element = await self.browser_manager.page.wait_for_selector(
                    'text=/Cash:/',
                    timeout=5000
                )
                if cash_element:
                    cash_text = await cash_element.text_content()
                    logger.info(f"✅ 登錄驗證成功，檢測到現金信息: {cash_text}")
                    return True
                    
            except Exception as e:
                logger.debug(f"檢查現金信息失敗: {e}")
                
                # 嘗試檢查其他登錄成功指標
                try:
                    level_element = await self.browser_manager.page.wait_for_selector(
                        'text=/Level/',
                        timeout=3000
                    )
                    if level_element:
                        logger.info("✅ 登錄驗證成功，檢測到用戶等級信息")
                        return True
                except:
                    pass
            
            logger.error("❌ 登錄驗證失敗：未找到登錄成功指標")
            return False
            
        except Exception as e:
            logger.error(f"❌ 驗證登錄成功時發生錯誤: {e}")
            return False
    
    async def logout(self) -> bool:
        """執行登出操作"""
        try:
            logger.info("🚪 開始執行登出...")
            
            # 查找登出鏈接
            logout_link = await self.browser_manager.page.query_selector('a[href*="logout"]')
            if logout_link:
                await logout_link.click()
                logger.info("✅ 已點擊登出鏈接")
                
                # 等待登出完成
                await asyncio.sleep(3)
                
                # 檢查是否成功登出
                current_url = self.browser_manager.page.url
                if self.success_indicators['outpost_url'] not in current_url:
                    logger.info("✅ 登出成功")
                    self.browser_manager.is_logged_in = False
                    return True
                else:
                    logger.error("❌ 登出失敗：仍在遊戲主頁")
                    return False
            else:
                logger.error("❌ 未找到登出鏈接")
                return False
                
        except Exception as e:
            logger.error(f"❌ 登出過程中發生錯誤: {e}")
            return False
    
    def _can_attempt_login(self) -> bool:
        """Check if login attempt is allowed."""
        if self._login_attempts >= self._max_login_attempts:
            logger.warning(f"Max login attempts ({self._max_login_attempts}) reached")
            return False
        
        if self._last_login_time:
            time_since_last = asyncio.get_event_loop().time() - self._last_login_time
            if time_since_last < self._login_cooldown:
                remaining = self._login_cooldown - time_since_last
                logger.warning(f"Login cooldown active, {remaining:.1f}s remaining")
                return False
        
        return True
    
    def _reset_login_attempts(self) -> None:
        """Reset login attempt counter."""
        self._login_attempts = 0
        self._last_login_time = asyncio.get_event_loop().time()
    
    async def _process_login_form(self, form_element) -> bool:
        """Process login form within a specific element."""
        try:
            # Find fields within the form
            username_input = await form_element.query_selector('input[type="text"], input[name*="user"]')
            password_input = await form_element.query_selector('input[type="password"]')
            submit_button = await form_element.query_selector('input[type="submit"], button[type="submit"]')
            
            if not username_input or not password_input:
                logger.error("Required form fields not found in dialog")
                return False
            
            # Fill form
            await username_input.fill(self.settings.username)
            await asyncio.sleep(0.5)
            await password_input.fill(self.settings.password)
            await asyncio.sleep(0.5)
            
            # Submit
            if submit_button:
                await submit_button.click()
            else:
                await form_element.evaluate('form => form.submit()')
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing login form: {e}")
            return False
    
    def get_login_status(self) -> Dict[str, Any]:
        """Get current login handler status."""
        return {
            'login_attempts': self._login_attempts,
            'max_attempts': self._max_login_attempts,
            'last_login_time': self._last_login_time,
            'cooldown_remaining': max(0, self._login_cooldown - (
                asyncio.get_event_loop().time() - self._last_login_time
            )) if self._last_login_time else 0,
            'can_attempt_login': self._can_attempt_login()
        }
    
    def reset_login_state(self) -> None:
        """Reset login handler state."""
        self._login_attempts = 0
        self._last_login_time = None
        logger.info("Login handler state reset") 