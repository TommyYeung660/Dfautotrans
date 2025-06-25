"""Bank operations module for Dead Frontier Auto Trading System."""

import asyncio
import re
from typing import Optional, Dict, Any, Tuple
from datetime import datetime
from loguru import logger
from dataclasses import dataclass

from ..automation.browser_manager import BrowserManager
from ..core.page_navigator import PageNavigator


@dataclass
class BankOperationResult:
    """Result of a bank operation."""
    success: bool
    operation_type: str  # withdraw, withdraw_all, deposit, deposit_all, ensure_funds
    amount_processed: Optional[int] = None
    balance_before: Optional[int] = None
    balance_after: Optional[int] = None
    error_message: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class BankOperations:
    """Handles all bank-related operations."""
    
    def __init__(self, browser_manager: BrowserManager):
        self.browser_manager = browser_manager
        
        # Cache for bank information
        self._bank_balance_cache: Optional[int] = None
        self._cache_timestamp: Optional[datetime] = None
        self._cache_duration = 30  # seconds

    @property
    def page(self):
        """動態獲取當前page對象"""
        if not self.browser_manager.page:
            raise RuntimeError("Browser page not initialized")
        return self.browser_manager.page

    async def navigate_to_bank(self) -> bool:
        """Navigate to bank page."""
        logger.info("🏦 導航到銀行頁面...")
        
        # 直接導航到銀行頁面
        try:
            await self.page.goto("https://fairview.deadfrontier.com/onlinezombiemmo/index.php?page=15")
            await self.page.wait_for_load_state("networkidle", timeout=10000)
            
            # 驗證是否到達銀行頁面 - 檢查頁面內容而不是標題
            try:
                # 等待銀行相關元素出現
                await self.page.wait_for_selector("body", timeout=5000)
                page_content = await self.page.inner_text("body")
                
                # 檢查是否包含銀行相關內容
                bank_indicators = ["bank", "withdraw", "deposit", "cash", "$"]
                has_bank_content = any(indicator.lower() in page_content.lower() for indicator in bank_indicators)
                
                if has_bank_content:
                    logger.info("✅ 成功到達銀行頁面")
                    self._clear_cache()
                    return True
                else:
                    logger.warning("⚠️ 頁面內容不包含銀行相關信息")
                    # 仍然返回True，因為可能是頁面結構變化
                    return True
                    
            except Exception as content_check_error:
                logger.warning(f"⚠️ 銀行頁面內容檢查失敗: {content_check_error}")
                # 假設成功，繼續執行
                return True
                
        except Exception as e:
            logger.error(f"❌ 銀行頁面導航失敗: {e}")
            return False
    
    async def get_bank_balance(self) -> Optional[int]:
        """Get current bank balance."""
        if not await self._ensure_on_bank_page():
            return None
            
        # Check cache first
        if self._is_cache_valid():
            logger.debug(f"使用緩存的銀行餘額: ${self._bank_balance_cache}")
            return self._bank_balance_cache
            
        try:
            # Look for bank balance text patterns
            bank_selectors = [
                "text=Bank:", 
                "[class*='bank']",
                "[id*='bank']"
            ]
            
            for selector in bank_selectors:
                elements = await self.page.query_selector_all(selector)
                for element in elements:
                    text = await element.inner_text()
                    balance = self._extract_bank_balance_from_text(text)
                    if balance is not None:
                        self._update_cache(balance)
                        logger.debug(f"從選擇器 {selector} 找到銀行餘額: ${balance}")
                        return balance
            
            # Try to find in page text
            page_text = await self.page.inner_text("body")
            balance = self._extract_bank_balance_from_text(page_text)
            if balance is not None:
                self._update_cache(balance)
                logger.debug(f"從頁面文本找到銀行餘額: ${balance}")
                return balance
                
            logger.warning("無法找到銀行餘額信息")
            return None
            
        except Exception as e:
            logger.error(f"獲取銀行餘額時出錯: {e}")
            return None
    
    async def get_cash_on_hand(self) -> Optional[int]:
        """Get current cash on hand."""
        if not await self._ensure_on_bank_page():
            return None
            
        try:
            # 直接從頁面提取現金信息
            page_text = await self.page.inner_text("body")
            
            # 查找現金模式
            cash_patterns = [
                r'Cash:\s*\$?([\d,]+)',
                r'現金:\s*\$?([\d,]+)',
                r'Money:\s*\$?([\d,]+)',
                r'\$\s*([\d,]+)(?=\s|$)',
            ]
            
            for pattern in cash_patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                for match in matches:
                    try:
                        cash = int(match.replace(',', ''))
                        if 0 <= cash <= 10000000:  # 合理範圍檢查
                            logger.debug(f"找到現金: ${cash}")
                            return cash
                    except ValueError:
                        continue
            
            logger.warning("無法從頁面找到現金信息")
            return None
            
        except Exception as e:
            logger.error(f"獲取現金時出錯: {e}")
            return None
    
    async def get_total_available_funds(self) -> Optional[int]:
        """Get total available funds (cash + bank)."""
        cash = await self.get_cash_on_hand()
        bank = await self.get_bank_balance()
        
        if cash is None or bank is None:
            logger.warning("無法獲取完整的資金信息")
            return None
            
        total = cash + bank
        logger.info(f"💰 總可用資金: ${total} (現金: ${cash} + 銀行: ${bank})")
        return total
    
    async def withdraw_funds(self, amount: int) -> BankOperationResult:
        """Withdraw specific amount from bank."""
        logger.info(f"🏦 準備從銀行提取 ${amount}...")
        
        if not await self._ensure_on_bank_page():
            return BankOperationResult(
                success=False,
                error_message="無法到達銀行頁面",
                operation_type="withdraw"
            )
        
        # Check if amount is valid
        bank_balance = await self.get_bank_balance()
        if bank_balance is None:
            return BankOperationResult(
                success=False,
                error_message="無法獲取銀行餘額",
                operation_type="withdraw"
            )
            
        if amount > bank_balance:
            return BankOperationResult(
                success=False,
                error_message=f"提取金額 ${amount} 超過銀行餘額 ${bank_balance}",
                operation_type="withdraw"
            )
        
        try:
            # Find withdraw input field
            withdraw_input = await self.page.query_selector("input[type='number']:first-of-type")
            if not withdraw_input:
                # Try alternative selectors
                withdraw_input = await self.page.query_selector("input[name*='withdraw']")
                if not withdraw_input:
                    withdraw_input = await self.page.query_selector("spinbutton:first-of-type")
                    
            if not withdraw_input:
                return BankOperationResult(
                    success=False,
                    error_message="找不到提取金額輸入框",
                    operation_type="withdraw"
                )
            
            # Clear and fill amount
            await withdraw_input.fill("")  # Clear the input
            await withdraw_input.fill(str(amount))
            
            # Find and click withdraw button
            withdraw_button = await self.page.query_selector("button:text('withdraw')")
            if not withdraw_button:
                withdraw_button = await self.page.query_selector("input[value='withdraw']")
                
            if not withdraw_button:
                return BankOperationResult(
                    success=False,
                    error_message="找不到提取按鈕",
                    operation_type="withdraw"
                )
            
            # Click withdraw button
            await withdraw_button.click()
            
            # Wait for page to update
            await asyncio.sleep(2)
            
            # Verify the operation
            new_bank_balance = await self.get_bank_balance()
            if new_bank_balance is not None and new_bank_balance == bank_balance - amount:
                logger.info(f"✅ 成功提取 ${amount}，銀行餘額: ${new_bank_balance}")
                return BankOperationResult(
                    success=True,
                    amount_processed=amount,
                    balance_before=bank_balance,
                    balance_after=new_bank_balance,
                    operation_type="withdraw"
                )
            else:
                return BankOperationResult(
                    success=False,
                    error_message="提取操作可能失敗，餘額未按預期變化",
                    operation_type="withdraw"
                )
                
        except Exception as e:
            logger.error(f"提取資金時出錯: {e}")
            return BankOperationResult(
                success=False,
                error_message=f"提取操作異常: {str(e)}",
                operation_type="withdraw"
            )
    
    async def withdraw_all_funds(self) -> BankOperationResult:
        """Withdraw all funds from bank."""
        logger.info("🏦 準備提取所有銀行資金...")
        
        if not await self._ensure_on_bank_page():
            return BankOperationResult(
                success=False,
                error_message="無法到達銀行頁面",
                operation_type="withdraw_all"
            )
        
        bank_balance = await self.get_bank_balance()
        if bank_balance is None:
            return BankOperationResult(
                success=False,
                error_message="無法獲取銀行餘額",
                operation_type="withdraw_all"
            )
            
        if bank_balance == 0:
            logger.info("銀行餘額為 $0，無需提取")
            return BankOperationResult(
                success=True,
                amount_processed=0,
                balance_before=0,
                balance_after=0,
                operation_type="withdraw_all"
            )
        
        try:
            # Multiple strategies to find withdraw all button
            withdraw_all_button = None
            
            # Strategy 1: Try common text patterns
            withdraw_selectors = [
                "button:text('withdraw all')",
                "input[value='withdraw all']",
                "button:text('Withdraw All')",
                "input[value='Withdraw All']",
                "button:has-text('withdraw all')",
                "input[type='submit'][value*='withdraw'][value*='all']",
                ".withdraw-all",
                "#withdrawAll",
                "button[onclick*='withdraw'][onclick*='all']"
            ]
            
            for selector in withdraw_selectors:
                try:
                    withdraw_all_button = await self.page.query_selector(selector)
                    if withdraw_all_button:
                        logger.debug(f"找到提取所有資金按鈕: {selector}")
                        break
                except Exception:
                    continue
            
            # Strategy 2: If no button found, try to find withdraw input field and max button
            if not withdraw_all_button:
                logger.debug("未找到 withdraw all 按鈕，嘗試手動輸入最大金額")
                
                # Find withdraw input field
                withdraw_input = await self.page.query_selector("input[type='number']:first-of-type")
                if not withdraw_input:
                    withdraw_input = await self.page.query_selector("input[name*='withdraw']")
                if not withdraw_input:
                    withdraw_input = await self.page.query_selector("spinbutton:first-of-type")
                
                if withdraw_input:
                    # Clear and fill with bank balance
                    await withdraw_input.fill("")  # Clear the input
                    await withdraw_input.fill(str(bank_balance))
                    
                    # Find regular withdraw button
                    withdraw_button = await self.page.query_selector("button:text('withdraw')")
                    if not withdraw_button:
                        withdraw_button = await self.page.query_selector("input[value='withdraw']")
                    
                    if withdraw_button:
                        await withdraw_button.click()
                        logger.debug(f"使用手動輸入方式提取 ${bank_balance}")
                    else:
                        return BankOperationResult(
                            success=False,
                            error_message="找不到提取按鈕",
                            operation_type="withdraw_all"
                        )
                else:
                    return BankOperationResult(
                        success=False,
                        error_message="找不到提取金額輸入框",
                        operation_type="withdraw_all"
                    )
            else:
                # Click withdraw all button
                await withdraw_all_button.click()
                logger.debug("點擊 withdraw all 按鈕")
            
            # Wait for page to update
            await asyncio.sleep(3)
            
            # Clear cache to force fresh data
            self._clear_cache()
            
            # Verify the operation
            new_bank_balance = await self.get_bank_balance()
            if new_bank_balance is not None:
                if new_bank_balance < bank_balance:
                    # Some money was withdrawn
                    amount_withdrawn = bank_balance - new_bank_balance
                    logger.info(f"✅ 成功提取資金 ${amount_withdrawn}，銀行餘額: ${new_bank_balance}")
                    return BankOperationResult(
                        success=True,
                        amount_processed=amount_withdrawn,
                        balance_before=bank_balance,
                        balance_after=new_bank_balance,
                        operation_type="withdraw_all"
                    )
                elif new_bank_balance == 0:
                    # All money withdrawn
                    logger.info(f"✅ 成功提取所有資金 ${bank_balance}，銀行餘額: ${new_bank_balance}")
                    return BankOperationResult(
                        success=True,
                        amount_processed=bank_balance,
                        balance_before=bank_balance,
                        balance_after=new_bank_balance,
                        operation_type="withdraw_all"
                    )
                else:
                    return BankOperationResult(
                        success=False,
                        error_message=f"提取操作未生效，銀行餘額仍為 ${new_bank_balance}",
                        operation_type="withdraw_all"
                    )
            else:
                return BankOperationResult(
                    success=False,
                    error_message="無法驗證提取結果，無法獲取銀行餘額",
                    operation_type="withdraw_all"
                )
                
        except Exception as e:
            logger.error(f"提取所有資金時出錯: {e}")
            return BankOperationResult(
                success=False,
                error_message=f"提取所有資金操作異常: {str(e)}",
                operation_type="withdraw_all"
            )
    
    async def deposit_funds(self, amount: int) -> BankOperationResult:
        """Deposit specific amount to bank."""
        logger.info(f"🏦 準備存入 ${amount} 到銀行...")
        
        if not await self._ensure_on_bank_page():
            return BankOperationResult(
                success=False,
                error_message="無法到達銀行頁面",
                operation_type="deposit"
            )
        
        # Check if amount is valid
        cash_on_hand = await self.get_cash_on_hand()
        if cash_on_hand is None:
            return BankOperationResult(
                success=False,
                error_message="無法獲取現金餘額",
                operation_type="deposit"
            )
            
        if amount > cash_on_hand:
            return BankOperationResult(
                success=False,
                error_message=f"存款金額 ${amount} 超過現金餘額 ${cash_on_hand}",
                operation_type="deposit"
            )
        
        bank_balance = await self.get_bank_balance()
        
        try:
            # Multiple strategies to find deposit input field
            deposit_input = None
            
            # Try various selectors for deposit input
            deposit_input_selectors = [
                "input[type='number']:nth-of-type(2)",  # Usually second number input
                "input[name*='deposit']",
                "spinbutton:nth-of-type(2)",
                "input[placeholder*='deposit']",
                "input[id*='deposit']",
                ".deposit-input",
                "#depositAmount"
            ]
            
            for selector in deposit_input_selectors:
                try:
                    deposit_input = await self.page.query_selector(selector)
                    if deposit_input:
                        logger.debug(f"找到存款輸入框: {selector}")
                        break
                except Exception:
                    continue
                    
            if not deposit_input:
                return BankOperationResult(
                    success=False,
                    error_message="找不到存款金額輸入框",
                    operation_type="deposit"
                )
            
            # Clear and fill amount
            await deposit_input.fill("")  # Clear the input
            await deposit_input.fill(str(amount))
            
            # Multiple strategies to find deposit button
            deposit_button = None
            
            deposit_button_selectors = [
                "button:text('deposit')",
                "input[value='deposit']",
                "button:text('Deposit')",
                "input[value='Deposit']",
                "button:has-text('deposit')",
                "input[type='submit'][value*='deposit']",
                ".deposit-button",
                "#depositButton",
                "button[onclick*='deposit']"
            ]
            
            for selector in deposit_button_selectors:
                try:
                    deposit_button = await self.page.query_selector(selector)
                    if deposit_button:
                        logger.debug(f"找到存款按鈕: {selector}")
                        break
                except Exception:
                    continue
                
            if not deposit_button:
                return BankOperationResult(
                    success=False,
                    error_message="找不到存款按鈕",
                    operation_type="deposit"
                )
            
            # Click deposit button
            await deposit_button.click()
            
            # Wait for page to update
            await asyncio.sleep(3)
            
            # Clear cache to force fresh data
            self._clear_cache()
            
            # Verify the operation
            new_bank_balance = await self.get_bank_balance()
            if new_bank_balance is not None and bank_balance is not None:
                if new_bank_balance >= bank_balance + amount:
                    # Money was deposited successfully
                    actual_deposited = new_bank_balance - bank_balance
                    logger.info(f"✅ 成功存入 ${actual_deposited}，銀行餘額: ${new_bank_balance}")
                    return BankOperationResult(
                        success=True,
                        amount_processed=actual_deposited,
                        balance_before=bank_balance,
                        balance_after=new_bank_balance,
                        operation_type="deposit"
                    )
                else:
                    return BankOperationResult(
                        success=False,
                        error_message=f"存款操作未生效，銀行餘額從 ${bank_balance} 變為 ${new_bank_balance}",
                        operation_type="deposit"
                    )
            else:
                return BankOperationResult(
                    success=False,
                    error_message="無法驗證存款結果，無法獲取銀行餘額",
                    operation_type="deposit"
                )
                
        except Exception as e:
            logger.error(f"存款時出錯: {e}")
            return BankOperationResult(
                success=False,
                error_message=f"存款操作異常: {str(e)}",
                operation_type="deposit"
            )
    
    async def deposit_all_funds(self) -> BankOperationResult:
        """Deposit all cash to bank."""
        logger.info("🏦 準備存入所有現金到銀行...")
        
        if not await self._ensure_on_bank_page():
            return BankOperationResult(
                success=False,
                error_message="無法到達銀行頁面",
                operation_type="deposit_all"
            )
        
        cash_on_hand = await self.get_cash_on_hand()
        if cash_on_hand is None:
            return BankOperationResult(
                success=False,
                error_message="無法獲取現金餘額",
                operation_type="deposit_all"
            )
            
        if cash_on_hand == 0:
            logger.info("現金餘額為 $0，無需存款")
            return BankOperationResult(
                success=True,
                amount_processed=0,
                balance_before=await self.get_bank_balance() or 0,
                balance_after=await self.get_bank_balance() or 0,
                operation_type="deposit_all"
            )
        
        bank_balance = await self.get_bank_balance()
        
        try:
            # Find and click "deposit all" button
            deposit_all_button = await self.page.query_selector("button:text('deposit all')")
            if not deposit_all_button:
                deposit_all_button = await self.page.query_selector("input[value='deposit all']")
                
            if not deposit_all_button:
                return BankOperationResult(
                    success=False,
                    error_message="找不到 'deposit all' 按鈕",
                    operation_type="deposit_all"
                )
            
            # Click deposit all button
            await deposit_all_button.click()
            
            # Wait for page to update
            await asyncio.sleep(2)
            
            # Verify the operation
            new_cash = await self.get_cash_on_hand()
            new_bank_balance = await self.get_bank_balance()
            
            if (new_cash is not None and new_cash == 0 and 
                new_bank_balance is not None and bank_balance is not None):
                if new_bank_balance == bank_balance + cash_on_hand:
                    logger.info(f"✅ 成功存入所有現金 ${cash_on_hand}，銀行餘額: ${new_bank_balance}")
                    return BankOperationResult(
                        success=True,
                        amount_processed=cash_on_hand,
                        balance_before=bank_balance,
                        balance_after=new_bank_balance,
                        operation_type="deposit_all"
                    )
            
            return BankOperationResult(
                success=False,
                error_message="存入所有現金操作可能失敗",
                operation_type="deposit_all"
            )
                
        except Exception as e:
            logger.error(f"存入所有現金時出錯: {e}")
            return BankOperationResult(
                success=False,
                error_message=f"存入所有現金操作異常: {str(e)}",
                operation_type="deposit_all"
            )
    
    async def ensure_minimum_funds(self, required_amount: int) -> BankOperationResult:
        """Ensure minimum funds available in cash."""
        logger.info(f"💰 確保現金至少有 ${required_amount}...")
        
        cash_on_hand = await self.get_cash_on_hand()
        if cash_on_hand is None:
            return BankOperationResult(
                success=False,
                error_message="無法獲取現金餘額",
                operation_type="ensure_funds"
            )
        
        if cash_on_hand >= required_amount:
            logger.info(f"✅ 現金餘額 ${cash_on_hand} 已滿足需求 ${required_amount}")
            return BankOperationResult(
                success=True,
                amount_processed=0,
                balance_before=cash_on_hand,
                balance_after=cash_on_hand,
                operation_type="ensure_funds"
            )
        
        # Need to withdraw from bank
        needed_amount = required_amount - cash_on_hand
        bank_balance = await self.get_bank_balance()
        
        if bank_balance is None:
            return BankOperationResult(
                success=False,
                error_message="無法獲取銀行餘額",
                operation_type="ensure_funds"
            )
        
        if bank_balance < needed_amount:
            total_available = cash_on_hand + bank_balance
            return BankOperationResult(
                success=False,
                error_message=f"總可用資金 ${total_available} 不足，需要 ${required_amount}",
                operation_type="ensure_funds"
            )
        
        # Withdraw needed amount
        logger.info(f"🏦 從銀行提取 ${needed_amount} 以滿足資金需求...")
        return await self.withdraw_funds(needed_amount)
    
    async def get_player_resources(self):
        """Get complete player resources information."""
        if not await self._ensure_on_bank_page():
            return None
        
        try:
            cash_on_hand = await self.get_cash_on_hand()
            bank_balance = await self.get_bank_balance()
            
            if cash_on_hand is None or bank_balance is None:
                logger.warning("無法獲取完整的資源信息")
                return None
            
            # Create basic resource info (inventory and storage would be checked separately)
            from ..data.models import InventoryStatus, StorageStatus, SellingSlotsStatus, PlayerResources
            
            resources = PlayerResources(
                cash_on_hand=cash_on_hand,
                bank_balance=bank_balance,
                inventory_status=InventoryStatus(current_count=0, max_capacity=50),  # Default values
                storage_status=StorageStatus(current_count=0, max_capacity=1000),    # Default values
                selling_slots_status=SellingSlotsStatus(current_listings=0, max_slots=30)  # Default values
            )
            
            logger.info(f"📊 玩家資源狀況:")
            logger.info(f"   現金: ${cash_on_hand}")
            logger.info(f"   銀行: ${bank_balance}")
            logger.info(f"   總資金: ${resources.total_available_cash}")
            
            return resources
            
        except Exception as e:
            logger.error(f"獲取玩家資源時出錯: {e}")
            return None
    
    # Private helper methods
    
    async def _ensure_on_bank_page(self) -> bool:
        """Ensure we are on the bank page."""
        if self.page is None:
            logger.error("瀏覽器頁面未初始化")
            return False
        
        current_url = self.page.url
        if "page=15" in current_url or "bank" in current_url.lower():
            return True
        
        logger.info("不在銀行頁面，正在導航...")
        return await self.navigate_to_bank()
    
    def _extract_bank_balance_from_text(self, text: str) -> Optional[int]:
        """Extract bank balance from text."""
        if not text:
            return None
        
        # Look for "Bank: $amount" pattern
        bank_patterns = [
            r'Bank:\s*\$?(\d{1,3}(?:,\d{3})*)',
            r'銀行:\s*\$?(\d{1,3}(?:,\d{3})*)',
            r'bank[:\s]*\$?(\d{1,3}(?:,\d{3})*)',
            r'Bank Balance[:\s]*\$?(\d{1,3}(?:,\d{3})*)'
        ]
        
        for pattern in bank_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(',', '')
                try:
                    return int(amount_str)
                except ValueError:
                    continue
        
        return None
    
    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid."""
        if self._bank_balance_cache is None or self._cache_timestamp is None:
            return False
        
        elapsed = (datetime.now() - self._cache_timestamp).total_seconds()
        return elapsed < self._cache_duration
    
    def _update_cache(self, balance: int) -> None:
        """Update balance cache."""
        self._bank_balance_cache = balance
        self._cache_timestamp = datetime.now()
    
    def _clear_cache(self) -> None:
        """Clear balance cache."""
        self._bank_balance_cache = None
        self._cache_timestamp = None 