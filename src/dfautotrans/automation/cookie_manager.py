"""Cookie management for Dead Frontier Auto Trading System."""

import json
import asyncio
from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime, timedelta
from playwright.async_api import Page, BrowserContext
from loguru import logger

from ..config.settings import Settings
from ..data.database import DatabaseManager


class CookieManager:
    """Manages browser cookies for persistent login sessions."""
    
    def __init__(self, settings: Settings, database_manager: Optional[DatabaseManager] = None):
        self.settings = settings
        self.database_manager = database_manager
        
        # Cookie storage paths
        self.cookies_dir = self.settings.project_root / "cache" / "cookies"
        self.cookies_dir.mkdir(parents=True, exist_ok=True)
        
        self.session_file = self.cookies_dir / "session.json"
        self.cookies_file = self.cookies_dir / "cookies.json"
        
        # Session validation settings
        self.session_timeout = timedelta(hours=24)  # 24小時會話超時
        self.cookie_domains = [
            "deadfrontier.com",
            "www.deadfrontier.com", 
            "fairview.deadfrontier.com"
        ]
        
        logger.info(f"Cookie manager initialized, storage: {self.cookies_dir}")
    
    async def save_session(self, context: BrowserContext, page: Page) -> bool:
        """Save current browser session (cookies + session info)."""
        try:
            # Get all cookies
            cookies = await context.cookies()
            
            # Filter relevant cookies
            relevant_cookies = [
                cookie for cookie in cookies 
                if any(domain in cookie.get('domain', '') for domain in self.cookie_domains)
            ]
            
            if not relevant_cookies:
                logger.warning("No relevant cookies found to save")
                return False
            
            # Get current URL and user info
            current_url = page.url if page else ""
            
            # Try to extract user info from page
            user_info = await self._extract_user_info(page)
            
            # Create session data
            session_data = {
                "timestamp": datetime.now().isoformat(),
                "cookies": relevant_cookies,
                "last_url": current_url,
                "user_info": user_info,
                "session_valid": True,
                "expires_at": (datetime.now() + self.session_timeout).isoformat()
            }
            
            # Save to file
            with open(self.session_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, indent=2, ensure_ascii=False)
            
            # Also save cookies separately for backup
            with open(self.cookies_file, 'w', encoding='utf-8') as f:
                json.dump(relevant_cookies, f, indent=2, ensure_ascii=False)
            
            # Save to database if available
            if self.database_manager:
                await self._save_session_to_db(session_data)
            
            logger.info(f"✅ 會話已保存: {len(relevant_cookies)} cookies, 用戶: {user_info.get('username', 'Unknown')}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 保存會話失敗: {e}")
            return False
    
    async def load_session(self, context: BrowserContext) -> bool:
        """Load saved browser session."""
        try:
            # Try loading from file first
            session_data = await self._load_session_from_file()
            
            # If file not available, try database
            if not session_data and self.database_manager:
                session_data = await self._load_session_from_db()
            
            if not session_data:
                logger.info("沒有找到保存的會話")
                return False
            
            # Check if session is still valid
            if not await self._is_session_valid(session_data):
                logger.info("保存的會話已過期")
                await self.clear_session()
                return False
            
            # Load cookies into context
            cookies = session_data.get("cookies", [])
            if cookies:
                await context.add_cookies(cookies)
                logger.info(f"✅ 已恢復會話: {len(cookies)} cookies")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ 加載會話失敗: {e}")
            return False
    
    async def validate_session(self, page: Page) -> bool:
        """Validate if current session is still active."""
        try:
            # Check if we're on a logged-in page
            current_url = page.url
            
            # If we're on login page, session is invalid
            if "autologin=1" in current_url or "login" in current_url.lower():
                return False
            
            # If we're on fairview domain, check for user indicators
            if "fairview.deadfrontier.com" in current_url:
                # Check for game elements that indicate logged-in state
                game_elements = [
                    "generic:has-text('Cash:')",
                    "generic:has-text('Level')",
                    "a[href*='logout']"
                ]
                
                for selector in game_elements:
                    try:
                        element = await page.wait_for_selector(selector, timeout=3000)
                        if element:
                            logger.debug(f"會話驗證成功: 找到 {selector}")
                            return True
                    except:
                        continue
                
                # Check page content
                try:
                    page_content = await page.content()
                    if any(indicator in page_content.lower() for indicator in ["cash:", "level:", "logout"]):
                        logger.debug("會話驗證成功: 在頁面內容中找到用戶信息")
                        return True
                except:
                    pass
            
            # Try to navigate to a protected page to test session
            logger.debug("嘗試導航到受保護頁面驗證會話...")
            response = await page.goto(
                "https://fairview.deadfrontier.com/onlinezombiemmo/index.php",
                wait_until="domcontentloaded",
                timeout=10000
            )
            
            if response and response.ok:
                # Check if we landed on the game page
                await asyncio.sleep(2)  # Wait for page to load
                current_url = page.url
                
                if "fairview.deadfrontier.com" in current_url and "autologin" not in current_url:
                    logger.info("✅ 會話驗證成功")
                    return True
            
            logger.info("❌ 會話驗證失敗")
            return False
            
        except Exception as e:
            logger.error(f"會話驗證出錯: {e}")
            return False
    
    async def clear_session(self) -> None:
        """Clear saved session data."""
        try:
            # Remove files
            if self.session_file.exists():
                self.session_file.unlink()
                logger.debug("已刪除會話文件")
            
            if self.cookies_file.exists():
                self.cookies_file.unlink()
                logger.debug("已刪除 cookies 文件")
            
            # Clear from database
            if self.database_manager:
                await self._clear_session_from_db()
            
            logger.info("✅ 會話數據已清除")
            
        except Exception as e:
            logger.error(f"清除會話數據失敗: {e}")
    
    async def get_session_info(self) -> Optional[Dict[str, Any]]:
        """Get information about current saved session."""
        try:
            session_data = await self._load_session_from_file()
            
            if not session_data:
                return None
            
            return {
                "saved_at": session_data.get("timestamp"),
                "expires_at": session_data.get("expires_at"),
                "last_url": session_data.get("last_url"),
                "user_info": session_data.get("user_info", {}),
                "cookie_count": len(session_data.get("cookies", [])),
                "is_valid": await self._is_session_valid(session_data)
            }
            
        except Exception as e:
            logger.error(f"獲取會話信息失敗: {e}")
            return None
    
    # Private helper methods
    
    async def _extract_user_info(self, page: Page) -> Dict[str, Any]:
        """Extract user information from current page."""
        user_info = {}
        
        try:
            # Try to get username from page
            username_selectors = [
                "text=/\\w+/",  # Generic username pattern
                ".username",
                ".player-name",
                "#username"
            ]
            
            for selector in username_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        text = await element.inner_text()
                        if text and len(text.strip()) > 0:
                            user_info["username"] = text.strip()
                            break
                except:
                    continue
            
            # Try to get cash amount
            try:
                cash_element = await page.query_selector('text=/Cash: \\$[\\d,]+/')
                if cash_element:
                    cash_text = await cash_element.inner_text()
                    # Extract number from "Cash: $123,456"
                    import re
                    match = re.search(r'\$([0-9,]+)', cash_text)
                    if match:
                        user_info["cash"] = match.group(1)
            except:
                pass
            
            # Try to get level
            try:
                level_element = await page.query_selector('text=/Level \\d+/')
                if level_element:
                    level_text = await level_element.inner_text()
                    import re
                    match = re.search(r'Level (\d+)', level_text)
                    if match:
                        user_info["level"] = int(match.group(1))
            except:
                pass
            
        except Exception as e:
            logger.debug(f"提取用戶信息時出錯: {e}")
        
        return user_info
    
    async def _load_session_from_file(self) -> Optional[Dict[str, Any]]:
        """Load session data from file."""
        try:
            if not self.session_file.exists():
                return None
            
            with open(self.session_file, 'r', encoding='utf-8') as f:
                return json.load(f)
                
        except Exception as e:
            logger.debug(f"從文件加載會話失敗: {e}")
            return None
    
    async def _is_session_valid(self, session_data: Dict[str, Any]) -> bool:
        """Check if session data is still valid."""
        try:
            # Check expiration time
            expires_at_str = session_data.get("expires_at")
            if expires_at_str:
                expires_at = datetime.fromisoformat(expires_at_str)
                if datetime.now() > expires_at:
                    logger.debug("會話已過期")
                    return False
            
            # Check if session is marked as valid
            if not session_data.get("session_valid", False):
                logger.debug("會話標記為無效")
                return False
            
            # Check if cookies exist
            cookies = session_data.get("cookies", [])
            if not cookies:
                logger.debug("會話中沒有 cookies")
                return False
            
            return True
            
        except Exception as e:
            logger.debug(f"驗證會話數據失敗: {e}")
            return False
    
    async def _save_session_to_db(self, session_data: Dict[str, Any]) -> None:
        """Save session data to database."""
        try:
            if not self.database_manager:
                return
            
            # Convert session data to JSON string for storage
            session_json = json.dumps(session_data, ensure_ascii=False)
            
            async with self.database_manager.get_session() as session:
                # Save as system state
                await self.database_manager.save_system_state({
                    "current_state": "SESSION_SAVED",
                    "state_data": session_json
                })
            
            logger.debug("會話數據已保存到數據庫")
            
        except Exception as e:
            logger.debug(f"保存會話到數據庫失敗: {e}")
    
    async def _load_session_from_db(self) -> Optional[Dict[str, Any]]:
        """Load session data from database."""
        try:
            if not self.database_manager:
                return None
            
            # Implementation would depend on database schema
            # For now, return None
            return None
            
        except Exception as e:
            logger.debug(f"從數據庫加載會話失敗: {e}")
            return None
    
    async def _clear_session_from_db(self) -> None:
        """Clear session data from database."""
        try:
            if not self.database_manager:
                return
            
            # Implementation would depend on database schema
            logger.debug("數據庫會話數據已清除")
            
        except Exception as e:
            logger.debug(f"清除數據庫會話失敗: {e}") 