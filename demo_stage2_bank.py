#!/usr/bin/env python3
"""
Dead Frontier Auto Trading System - Stage 2 Bank Operations Demo
階段2演示：銀行操作模組 - 資金管理
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
from src.dfautotrans.core.state_machine import StateMachine


class Stage2BankDemo:
    """階段2銀行操作演示"""
    
    def __init__(self):
        self.settings = Settings()
        self.browser_manager = None
        self.login_handler = None
        self.page_navigator = None
        self.bank_operations = None
        self.database_manager = None
        self.state_machine = None
        
    async def initialize(self):
        """初始化所有組件"""
        logger.info("🚀 初始化階段2銀行操作演示系統...")
        
        try:
            # 1. 初始化數據庫
            self.database_manager = DatabaseManager(self.settings)
            await self.database_manager.initialize()
            logger.info("✅ 數據庫管理器初始化完成")
            
            # 2. 初始化瀏覽器管理器
            self.browser_manager = BrowserManager(self.settings)
            await self.browser_manager.initialize()
            logger.info("✅ 瀏覽器管理器初始化完成")
            
            # 3. 初始化頁面導航器
            self.page_navigator = PageNavigator(self.browser_manager, self.settings)
            await self.page_navigator.initialize()
            logger.info("✅ 頁面導航器初始化完成")
            
            # 4. 初始化登錄處理器
            self.login_handler = LoginHandler(self.browser_manager, self.page_navigator, self.settings)
            logger.info("✅ 登錄處理器初始化完成")
            
            # 5. 初始化銀行操作模組
            self.bank_operations = BankOperations(self.settings, self.browser_manager, self.page_navigator)
            logger.info("✅ 銀行操作模組初始化完成")
            
            # 6. 初始化狀態機
            self.state_machine = StateMachine(self.settings)
            logger.info("✅ 狀態機初始化完成")
            
            logger.info("🎉 所有組件初始化完成！")
            return True
            
        except Exception as e:
            logger.error(f"❌ 初始化失敗: {e}")
            return False
    
    async def demonstrate_login_and_navigation(self):
        """演示登錄和導航功能"""
        logger.info("\n" + "="*60)
        logger.info("🔐 開始演示登錄和導航功能")
        logger.info("="*60)
        
        # 1. 確保登錄
        logger.info("1️⃣ 檢查登錄狀態...")
        login_success = await self.page_navigator.ensure_logged_in()
        if not login_success:
            logger.info("需要登錄，執行登錄流程...")
            login_success = await self.login_handler.perform_login()
        
        if login_success:
            logger.info("✅ 登錄成功")
        else:
            logger.error("❌ 登錄失敗")
            return False
        
        # 2. 導航到銀行頁面
        logger.info("2️⃣ 導航到銀行頁面...")
        bank_nav_success = await self.bank_operations.navigate_to_bank()
        if bank_nav_success:
            logger.info("✅ 成功到達銀行頁面")
        else:
            logger.error("❌ 銀行導航失敗")
            return False
        
        return True
    
    async def demonstrate_bank_information_retrieval(self):
        """演示銀行信息獲取功能"""
        logger.info("\n" + "="*60)
        logger.info("💰 開始演示銀行信息獲取功能")
        logger.info("="*60)
        
        # 1. 獲取現金餘額
        logger.info("1️⃣ 獲取現金餘額...")
        cash_on_hand = await self.bank_operations.get_cash_on_hand()
        if cash_on_hand is not None:
            logger.info(f"✅ 現金餘額: ${cash_on_hand:,}")
        else:
            logger.error("❌ 無法獲取現金餘額")
        
        # 2. 獲取銀行餘額
        logger.info("2️⃣ 獲取銀行餘額...")
        bank_balance = await self.bank_operations.get_bank_balance()
        if bank_balance is not None:
            logger.info(f"✅ 銀行餘額: ${bank_balance:,}")
        else:
            logger.error("❌ 無法獲取銀行餘額")
        
        # 3. 獲取總可用資金
        logger.info("3️⃣ 計算總可用資金...")
        total_funds = await self.bank_operations.get_total_available_funds()
        if total_funds is not None:
            logger.info(f"✅ 總可用資金: ${total_funds:,}")
        else:
            logger.error("❌ 無法計算總可用資金")
        
        # 4. 獲取完整玩家資源
        logger.info("4️⃣ 獲取完整玩家資源...")
        player_resources = await self.bank_operations.get_player_resources()
        if player_resources:
            logger.info("✅ 玩家資源獲取成功:")
            logger.info(f"   現金: ${player_resources.cash_on_hand:,}")
            logger.info(f"   銀行: ${player_resources.bank_balance:,}")
            logger.info(f"   總資金: ${player_resources.total_available_cash:,}")
            logger.info(f"   可交易: {'是' if player_resources.can_trade else '否'}")
        else:
            logger.error("❌ 無法獲取玩家資源")
        
        return cash_on_hand, bank_balance, total_funds
    
    async def demonstrate_withdraw_operations(self, bank_balance: int):
        """演示提取操作"""
        logger.info("\n" + "="*60)
        logger.info("🏦 開始演示提取操作")
        logger.info("="*60)
        
        if bank_balance <= 0:
            logger.info("⚠️  銀行餘額為 $0，跳過提取操作演示")
            return
        
        # 1. 提取小額資金測試
        test_amount = min(1000, bank_balance // 2)
        logger.info(f"1️⃣ 測試提取 ${test_amount}...")
        
        withdraw_result = await self.bank_operations.withdraw_funds(test_amount)
        if withdraw_result.success:
            logger.info(f"✅ 提取成功:")
            logger.info(f"   提取金額: ${withdraw_result.amount_processed:,}")
            logger.info(f"   提取前餘額: ${withdraw_result.balance_before:,}")
            logger.info(f"   提取後餘額: ${withdraw_result.balance_after:,}")
        else:
            logger.error(f"❌ 提取失敗: {withdraw_result.error_message}")
        
        # 等待一下再繼續
        await asyncio.sleep(2)
        
        # 2. 測試提取所有資金
        logger.info("2️⃣ 測試提取所有銀行資金...")
        
        withdraw_all_result = await self.bank_operations.withdraw_all_funds()
        if withdraw_all_result.success:
            logger.info(f"✅ 提取所有資金成功:")
            logger.info(f"   提取金額: ${withdraw_all_result.amount_processed:,}")
            logger.info(f"   提取前餘額: ${withdraw_all_result.balance_before:,}")
            logger.info(f"   提取後餘額: ${withdraw_all_result.balance_after:,}")
        else:
            logger.error(f"❌ 提取所有資金失敗: {withdraw_all_result.error_message}")
        
        return withdraw_result, withdraw_all_result
    
    async def demonstrate_deposit_operations(self, cash_on_hand: int):
        """演示存款操作"""
        logger.info("\n" + "="*60)
        logger.info("🏦 開始演示存款操作")
        logger.info("="*60)
        
        if cash_on_hand <= 0:
            logger.info("⚠️  現金餘額為 $0，跳過存款操作演示")
            return
        
        # 1. 存入小額資金測試
        test_amount = min(1000, cash_on_hand // 2)
        logger.info(f"1️⃣ 測試存入 ${test_amount}...")
        
        deposit_result = await self.bank_operations.deposit_funds(test_amount)
        if deposit_result.success:
            logger.info(f"✅ 存款成功:")
            logger.info(f"   存款金額: ${deposit_result.amount_processed:,}")
            logger.info(f"   存款前餘額: ${deposit_result.balance_before:,}")
            logger.info(f"   存款後餘額: ${deposit_result.balance_after:,}")
        else:
            logger.error(f"❌ 存款失敗: {deposit_result.error_message}")
        
        # 等待一下再繼續
        await asyncio.sleep(2)
        
        # 2. 測試存入所有現金
        logger.info("2️⃣ 測試存入所有現金...")
        
        deposit_all_result = await self.bank_operations.deposit_all_funds()
        if deposit_all_result.success:
            logger.info(f"✅ 存入所有現金成功:")
            logger.info(f"   存款金額: ${deposit_all_result.amount_processed:,}")
            logger.info(f"   存款前餘額: ${deposit_all_result.balance_before:,}")
            logger.info(f"   存款後餘額: ${deposit_all_result.balance_after:,}")
        else:
            logger.error(f"❌ 存入所有現金失敗: {deposit_all_result.error_message}")
        
        return deposit_result, deposit_all_result
    
    async def demonstrate_fund_management(self):
        """演示資金管理功能"""
        logger.info("\n" + "="*60)
        logger.info("💼 開始演示資金管理功能")
        logger.info("="*60)
        
        # 1. 確保最低資金測試
        required_amount = 50000
        logger.info(f"1️⃣ 確保現金至少有 ${required_amount:,}...")
        
        ensure_result = await self.bank_operations.ensure_minimum_funds(required_amount)
        if ensure_result.success:
            logger.info(f"✅ 資金確保成功:")
            if ensure_result.amount_processed > 0:
                logger.info(f"   從銀行提取: ${ensure_result.amount_processed:,}")
                logger.info(f"   提取前餘額: ${ensure_result.balance_before:,}")
                logger.info(f"   提取後餘額: ${ensure_result.balance_after:,}")
            else:
                logger.info(f"   現金已足夠，無需提取")
        else:
            logger.error(f"❌ 資金確保失敗: {ensure_result.error_message}")
        
        return ensure_result
    
    async def demonstrate_state_machine_integration(self):
        """演示狀態機集成"""
        logger.info("\n" + "="*60)
        logger.info("🔄 開始演示狀態機集成")
        logger.info("="*60)
        
        # 1. 狀態轉換演示
        logger.info("1️⃣ 演示銀行相關狀態轉換...")
        
        # 模擬檢查資源狀態
        self.state_machine.transition_to("CHECKING_RESOURCES")
        logger.info(f"當前狀態: {self.state_machine.current_state}")
        
        # 模擬資金不足狀態
        self.state_machine.transition_to("INSUFFICIENT_FUNDS")
        logger.info(f"當前狀態: {self.state_machine.current_state}")
        
        # 模擬從銀行提取狀態
        self.state_machine.transition_to("WITHDRAWING_FROM_BANK")
        logger.info(f"當前狀態: {self.state_machine.current_state}")
        
        # 返回檢查資源狀態
        self.state_machine.transition_to("CHECKING_RESOURCES")
        logger.info(f"當前狀態: {self.state_machine.current_state}")
        
        # 2. 獲取狀態統計
        logger.info("2️⃣ 獲取狀態機統計...")
        stats = self.state_machine.get_statistics()
        if stats:
            logger.info(f"✅ 狀態機統計:")
            logger.info(f"   總轉換次數: {stats['total_transitions']}")
            logger.info(f"   總持續時間: {stats['total_duration']:.1f} 秒")
            logger.info(f"   當前狀態持續時間: {stats['current_state_duration']:.1f} 秒")
        
        return True
    
    async def demonstrate_database_integration(self):
        """演示數據庫集成"""
        logger.info("\n" + "="*60)
        logger.info("📊 開始演示數據庫集成")
        logger.info("="*60)
        
        # 1. 創建交易會話
        logger.info("1️⃣ 創建交易會話...")
        session = await self.database_manager.create_trading_session(initial_cash=100000)
        if session:
            logger.info(f"✅ 創建交易會話成功，ID: {session.id}")
        else:
            logger.error("❌ 創建交易會話失敗")
            return
        
        # 2. 記錄銀行操作相關系統狀態
        logger.info("2️⃣ 記錄系統狀態...")
        state_success = await self.database_manager.save_system_state({
            "current_state": "WITHDRAWING_FROM_BANK",
            "session_id": session.id,
            "state_data": '{"operation": "withdraw_all", "stage": 2}'
        })
        if state_success:
            logger.info("✅ 系統狀態記錄成功")
        
        # 3. 記錄資源快照
        logger.info("3️⃣ 記錄資源快照...")
        player_resources = await self.bank_operations.get_player_resources()
        if player_resources:
            snapshot_success = await self.database_manager.save_resource_snapshot({
                "session_id": session.id,
                "cash_on_hand": player_resources.cash_on_hand,
                "bank_balance": player_resources.bank_balance,
                "inventory_count": player_resources.inventory_status.current_count,
                "storage_count": player_resources.storage_status.current_count,
                "selling_slots_used": player_resources.selling_slots_status.current_listings
            })
            if snapshot_success:
                logger.info("✅ 資源快照記錄成功")
        
        # 4. 獲取統計信息
        logger.info("4️⃣ 獲取統計信息...")
        stats = await self.database_manager.get_trading_statistics(session.id)
        if stats:
            logger.info(f"✅ 統計信息:")
            logger.info(f"   總交易數: {stats['total_trades']}")
            logger.info(f"   總利潤: ${stats['total_profit']:.2f}")
            logger.info(f"   平均利潤: ${stats['average_profit']:.2f}")
        
        return session.id
    
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
    
    async def run_full_demo(self):
        """運行完整演示"""
        logger.info("🎬 開始階段2銀行操作完整演示")
        logger.info("="*80)
        
        try:
            # 初始化
            if not await self.initialize():
                return False
            
            # 1. 登錄和導航
            if not await self.demonstrate_login_and_navigation():
                return False
            
            # 2. 銀行信息獲取
            cash, bank, total = await self.demonstrate_bank_information_retrieval()
            
            # 3. 提取操作演示
            if bank and bank > 0:
                await self.demonstrate_withdraw_operations(bank)
            
            # 4. 存款操作演示  
            current_cash = await self.bank_operations.get_cash_on_hand()
            if current_cash and current_cash > 0:
                await self.demonstrate_deposit_operations(current_cash)
            
            # 5. 資金管理演示
            await self.demonstrate_fund_management()
            
            # 6. 狀態機集成演示
            await self.demonstrate_state_machine_integration()
            
            # 7. 數據庫集成演示
            await self.demonstrate_database_integration()
            
            logger.info("\n" + "="*80)
            logger.info("🎉 階段2銀行操作演示完成！")
            logger.info("="*80)
            
            logger.info("📋 演示功能總結:")
            logger.info("✅ 登錄和銀行頁面導航")
            logger.info("✅ 銀行餘額和現金餘額獲取")
            logger.info("✅ 總可用資金計算")
            logger.info("✅ 指定金額提取功能")
            logger.info("✅ 全額提取功能")
            logger.info("✅ 指定金額存款功能")
            logger.info("✅ 全額存款功能")
            logger.info("✅ 最低資金確保功能")
            logger.info("✅ 完整玩家資源獲取")
            logger.info("✅ 狀態機集成")
            logger.info("✅ 數據庫集成")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 演示過程中出錯: {e}")
            return False
        
        finally:
            await self.cleanup()


async def main():
    """主函數"""
    demo = Stage2BankDemo()
    success = await demo.run_full_demo()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 