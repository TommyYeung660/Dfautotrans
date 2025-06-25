#!/usr/bin/env python3
"""
Dead Frontier Auto Trading System - Stage 2 Smart Login Demo
階段2智能登錄演示：Cookie 管理和會話恢復
"""

import asyncio
import sys
from pathlib import Path
from loguru import logger

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.dfautotrans.config.settings import Settings
from src.dfautotrans.automation.browser_manager import BrowserManager
from src.dfautotrans.automation.login_handler import LoginHandler
from src.dfautotrans.automation.bank_operations import BankOperations
from src.dfautotrans.core.page_navigator import PageNavigator
from src.dfautotrans.data.database import DatabaseManager


class SmartLoginDemo:
    """智能登錄演示類"""
    
    def __init__(self):
        self.settings = Settings()
        self.browser_manager = None
        self.login_handler = None
        self.page_navigator = None
        self.bank_operations = None
        self.database_manager = None
    
    async def initialize_components(self):
        """初始化所有組件"""
        logger.info("🚀 初始化組件...")
        
        # 1. 初始化數據庫管理器
        self.database_manager = DatabaseManager(self.settings)
        await self.database_manager.initialize()
        logger.info("✅ 數據庫管理器初始化完成")
        
        # 2. 初始化瀏覽器管理器
        self.browser_manager = BrowserManager(self.settings)
        await self.browser_manager.start()
        logger.info("✅ 瀏覽器管理器初始化完成")
        
        # 3. 初始化頁面導航器
        self.page_navigator = PageNavigator(self.browser_manager, self.settings)
        await self.page_navigator.initialize()
        logger.info("✅ 頁面導航器初始化完成")
        
        # 4. 初始化登錄處理器（包含 Cookie 管理）
        self.login_handler = LoginHandler(
            self.browser_manager, 
            self.page_navigator, 
            self.settings,
            self.database_manager
        )
        logger.info("✅ 登錄處理器初始化完成")
        
        # 5. 初始化銀行操作模組
        self.bank_operations = BankOperations(self.browser_manager)
        logger.info("✅ 銀行操作模組初始化完成")
    
    async def demonstrate_smart_login(self):
        """演示智能登錄功能"""
        logger.info("\n🎯 開始智能登錄演示...")
        
        # 1. 檢查是否有保存的會話
        logger.info("1️⃣ 檢查保存的會話信息...")
        session_info = await self.login_handler.cookie_manager.get_session_info()
        
        if session_info:
            logger.info("📋 找到保存的會話:")
            logger.info(f"   保存時間: {session_info.get('saved_at')}")
            logger.info(f"   過期時間: {session_info.get('expires_at')}")
            logger.info(f"   用戶信息: {session_info.get('user_info', {})}")
            logger.info(f"   Cookie 數量: {session_info.get('cookie_count', 0)}")
            logger.info(f"   會話有效: {session_info.get('is_valid', False)}")
        else:
            logger.info("📋 沒有找到保存的會話")
        
        # 2. 執行智能登錄
        logger.info("\n2️⃣ 執行智能登錄...")
        login_success = await self.login_handler.smart_login()
        
        if not login_success:
            logger.error("❌ 智能登錄失敗")
            return False
        
        # 3. 驗證登錄狀態
        logger.info("\n3️⃣ 驗證登錄狀態...")
        await asyncio.sleep(2)
        
        # 強制刷新檢查登錄狀態
        is_logged_in = await self.page_navigator.check_login_status(force_refresh=True)
        
        if is_logged_in:
            logger.info("✅ 登錄狀態驗證成功")
        else:
            logger.error("❌ 登錄狀態驗證失敗")
            return False
        
        # 4. 測試會話功能
        logger.info("\n4️⃣ 測試會話功能...")
        await self.test_session_functionality()
        
        return True
    
    async def test_session_functionality(self):
        """測試會話功能"""
        try:
            # 測試銀行頁面訪問
            logger.info("🏦 測試銀行頁面訪問...")
            await self.bank_operations.navigate_to_bank()
            
            # 獲取初始資金信息
            initial_cash = await self.bank_operations.get_cash_on_hand()
            initial_bank = await self.bank_operations.get_bank_balance()
            
            # 處理 None 值
            initial_cash = initial_cash or 0
            initial_bank = initial_bank or 0
            
            logger.info(f"💵 初始現金餘額: ${initial_cash:,}")
            logger.info(f"🏦 初始銀行餘額: ${initial_bank:,}")
            logger.info(f"💰 初始總可用資金: ${initial_cash + initial_bank:,}")
            
            # 演示銀行操作功能
            await self.demonstrate_bank_operations(initial_cash, initial_bank)
            
            # 測試其他頁面導航
            logger.info("\n🗺️ 測試其他頁面導航...")
            
            # 導航到主頁
            await self.page_navigator.navigate_to_url(
                "https://fairview.deadfrontier.com/onlinezombiemmo/index.php"
            )
            await asyncio.sleep(2)
            
            # 驗證仍然登錄
            is_still_logged_in = await self.page_navigator.check_login_status(force_refresh=True)
            
            if is_still_logged_in:
                logger.info("✅ 會話在頁面導航後仍然有效")
            else:
                logger.warning("⚠️ 會話在頁面導航後失效")
            
        except Exception as e:
            logger.error(f"❌ 會話功能測試失敗: {e}")
    
    async def demonstrate_bank_operations(self, initial_cash: int, initial_bank: int):
        """演示銀行操作功能"""
        logger.info("\n💰 演示銀行操作功能...")
        
        try:
            # 1. 演示取出所有存款
            if initial_bank > 0:
                logger.info(f"1️⃣ 演示取出所有存款（${initial_bank:,}）...")
                
                withdraw_result = await self.bank_operations.withdraw_all_funds()
                
                if withdraw_result.success:
                    logger.info("✅ 成功取出所有存款！")
                    logger.info(f"   取出金額: ${withdraw_result.amount_processed:,}")
                    logger.info(f"   操作前銀行餘額: ${withdraw_result.balance_before:,}")
                    logger.info(f"   操作後銀行餘額: ${withdraw_result.balance_after:,}")
                    
                    # 驗證現金增加
                    new_cash = await self.bank_operations.get_cash_on_hand() or 0
                    logger.info(f"   現金餘額更新: ${new_cash:,}")
                    
                    # 等待一下再進行下一步操作
                    await asyncio.sleep(3)
                    
                else:
                    logger.error(f"❌ 取出存款失敗: {withdraw_result.error_message}")
                    return
            else:
                logger.info("1️⃣ 銀行餘額為 $0，跳過取款演示")
            
            # 2. 演示存入部分現金
            current_cash = await self.bank_operations.get_cash_on_hand() or 0
            if current_cash > 10000:  # 如果現金超過 $10,000，存入一部分
                deposit_amount = 5000
                logger.info(f"\n2️⃣ 演示存入部分現金（${deposit_amount:,}）...")
                
                deposit_result = await self.bank_operations.deposit_funds(deposit_amount)
                
                if deposit_result.success:
                    logger.info("✅ 成功存入現金！")
                    logger.info(f"   存入金額: ${deposit_result.amount_processed:,}")
                    logger.info(f"   操作前銀行餘額: ${deposit_result.balance_before:,}")
                    logger.info(f"   操作後銀行餘額: ${deposit_result.balance_after:,}")
                    
                    # 驗證餘額變化
                    new_cash = await self.bank_operations.get_cash_on_hand() or 0
                    new_bank = await self.bank_operations.get_bank_balance() or 0
                    logger.info(f"   現金餘額更新: ${new_cash:,}")
                    logger.info(f"   銀行餘額更新: ${new_bank:,}")
                    
                    await asyncio.sleep(3)
                else:
                    logger.error(f"❌ 存入現金失敗: {deposit_result.error_message}")
            else:
                logger.info("2️⃣ 現金不足 $10,000，跳過存款演示")
            
            # 3. 演示獲取完整玩家資源
            logger.info("\n3️⃣ 演示獲取完整玩家資源...")
            player_resources = await self.bank_operations.get_player_resources()
            
            if player_resources:
                logger.info("✅ 成功獲取玩家資源:")
                logger.info(f"   現金: ${player_resources.cash_on_hand:,}")
                logger.info(f"   銀行: ${player_resources.bank_balance:,}")
                logger.info(f"   庫存狀態: {player_resources.inventory_status.current_count}/{player_resources.inventory_status.max_capacity}")
                logger.info(f"   倉庫狀態: {player_resources.storage_status.current_count}/{player_resources.storage_status.max_capacity}")
                logger.info(f"   銷售位狀態: {player_resources.selling_slots_status.current_listings}/{player_resources.selling_slots_status.max_slots}")
            else:
                logger.error("❌ 獲取玩家資源失敗")
            
            # 4. 演示資金需求檢查
            logger.info("\n4️⃣ 演示資金需求檢查...")
            required_amount = 50000  # 需要 $50,000
            
            ensure_result = await self.bank_operations.ensure_minimum_funds(required_amount)
            
            if ensure_result.success:
                logger.info(f"✅ 成功確保最低資金需求 ${required_amount:,}")
                if ensure_result.amount_processed and ensure_result.amount_processed > 0:
                    logger.info(f"   從銀行提取了: ${ensure_result.amount_processed:,}")
                else:
                    logger.info("   現金已足夠，無需提取")
            else:
                logger.error(f"❌ 無法滿足資金需求: {ensure_result.error_message}")
            
            # 5. 最終資金狀況
            logger.info("\n5️⃣ 最終資金狀況:")
            final_cash = await self.bank_operations.get_cash_on_hand() or 0
            final_bank = await self.bank_operations.get_bank_balance() or 0
            final_total = await self.bank_operations.get_total_available_funds() or 0
            
            logger.info(f"   最終現金餘額: ${final_cash:,}")
            logger.info(f"   最終銀行餘額: ${final_bank:,}")
            logger.info(f"   最終總可用資金: ${final_total:,}")
            
            # 資金變化總結
            cash_change = final_cash - initial_cash
            bank_change = final_bank - initial_bank
            
            logger.info(f"\n📊 資金變化總結:")
            logger.info(f"   現金變化: {'+' if cash_change >= 0 else ''}${cash_change:,}")
            logger.info(f"   銀行變化: {'+' if bank_change >= 0 else ''}${bank_change:,}")
            logger.info(f"   總資金變化: {'+' if (cash_change + bank_change) >= 0 else ''}${cash_change + bank_change:,}")
            
        except Exception as e:
            logger.error(f"❌ 銀行操作演示失敗: {e}")
    
    async def demonstrate_session_management(self):
        """演示會話管理功能"""
        logger.info("\n📊 演示會話管理功能...")
        
        # 1. 顯示當前會話信息
        logger.info("1️⃣ 當前會話信息:")
        session_info = await self.login_handler.cookie_manager.get_session_info()
        
        if session_info:
            logger.info(f"   用戶: {session_info.get('user_info', {}).get('username', 'Unknown')}")
            logger.info(f"   現金: ${session_info.get('user_info', {}).get('cash', 'Unknown')}")
            logger.info(f"   等級: {session_info.get('user_info', {}).get('level', 'Unknown')}")
            logger.info(f"   Cookie 數量: {session_info.get('cookie_count', 0)}")
        
        # 2. 手動保存當前會話
        logger.info("\n2️⃣ 手動保存當前會話...")
        save_success = await self.login_handler.cookie_manager.save_session(
            self.browser_manager.context,
            self.browser_manager.page
        )
        
        if save_success:
            logger.info("✅ 會話保存成功")
        else:
            logger.error("❌ 會話保存失敗")
        
        # 3. 再次檢查會話信息
        logger.info("\n3️⃣ 更新後的會話信息:")
        updated_session_info = await self.login_handler.cookie_manager.get_session_info()
        
        if updated_session_info:
            logger.info(f"   更新時間: {updated_session_info.get('saved_at')}")
            logger.info(f"   過期時間: {updated_session_info.get('expires_at')}")
            logger.info(f"   用戶信息: {updated_session_info.get('user_info', {})}")
    
    async def cleanup(self):
        """清理資源"""
        logger.info("\n🧹 清理資源...")
        
        try:
            if self.browser_manager:
                await self.browser_manager.cleanup()
                logger.info("✅ 瀏覽器管理器已關閉")
            
            if self.database_manager:
                await self.database_manager.close()
                logger.info("✅ 數據庫連接已關閉")
                
        except Exception as e:
            logger.error(f"❌ 清理過程中出錯: {e}")
    
    async def run(self):
        """運行演示"""
        try:
            logger.info("🎬 開始智能登錄演示...")
            
            # 初始化組件
            await self.initialize_components()
            
            # 演示智能登錄
            login_success = await self.demonstrate_smart_login()
            
            if login_success:
                # 演示會話管理
                await self.demonstrate_session_management()
                
                logger.info("\n🎉 智能登錄演示完成！")
                logger.info("主要功能:")
                logger.info("✅ Cookie 自動保存和恢復")
                logger.info("✅ 會話有效性驗證")
                logger.info("✅ 智能登錄流程")
                logger.info("✅ 會話管理功能")
            else:
                logger.error("\n❌ 智能登錄演示失敗")
                
        except Exception as e:
            logger.error(f"❌ 演示過程中發生錯誤: {e}")
        finally:
            await self.cleanup()


async def main():
    """主函數"""
    demo = SmartLoginDemo()
    await demo.run()


if __name__ == "__main__":
    asyncio.run(main()) 