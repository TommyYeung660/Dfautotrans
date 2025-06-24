#!/usr/bin/env python3
"""
Dead Frontier Auto Trading System - Stage 2 Bank Operations Simple Demo
階段2簡化演示：銀行操作模組 - 登錄和基本功能
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


class Stage2SimpleDemo:
    """階段2簡化銀行操作演示"""
    
    def __init__(self):
        self.settings = Settings()
        self.browser_manager = None
        self.login_handler = None
        self.page_navigator = None
        self.bank_operations = None
        
    async def initialize(self):
        """初始化組件"""
        logger.info("🚀 初始化階段2銀行操作演示系統...")
        
        try:
            # 1. 初始化瀏覽器管理器
            self.browser_manager = BrowserManager(self.settings)
            await self.browser_manager.initialize()
            logger.info("✅ 瀏覽器管理器初始化完成")
            
            # 2. 初始化頁面導航器
            self.page_navigator = PageNavigator(self.browser_manager, self.settings)
            await self.page_navigator.initialize()
            logger.info("✅ 頁面導航器初始化完成")
            
            # 3. 初始化登錄處理器
            self.login_handler = LoginHandler(self.browser_manager, self.page_navigator, self.settings)
            logger.info("✅ 登錄處理器初始化完成")
            
            # 4. 初始化銀行操作模組
            self.bank_operations = BankOperations(self.settings, self.browser_manager, self.page_navigator)
            logger.info("✅ 銀行操作模組初始化完成")
            
            logger.info("🎉 所有組件初始化完成！")
            return True
            
        except Exception as e:
            logger.error(f"❌ 初始化失敗: {e}")
            return False
    
    async def demonstrate_login_process(self):
        """演示完整登錄流程"""
        logger.info("\n" + "="*60)
        logger.info("🔐 開始演示登錄流程")
        logger.info("="*60)
        
        # 1. 檢查當前登錄狀態
        logger.info("1️⃣ 檢查當前登錄狀態...")
        is_logged_in = await self.login_handler.check_login_status()
        logger.info(f"當前登錄狀態: {'已登錄' if is_logged_in else '未登錄'}")
        
        if is_logged_in:
            logger.info("✅ 用戶已登錄，跳過登錄步驟")
            return True
        
        # 2. 執行登錄
        logger.info("2️⃣ 執行登錄流程...")
        logger.info(f"使用用戶名: {self.settings.username}")
        
        login_success = await self.login_handler.perform_login()
        
        if login_success:
            logger.info("✅ 登錄成功！")
            
            # 3. 驗證登錄狀態
            logger.info("3️⃣ 驗證登錄狀態...")
            await asyncio.sleep(3)  # 等待頁面完全加載
            
            # 清除緩存確保重新檢查
            self.page_navigator.clear_cache()
            
            is_logged_in = await self.login_handler.check_login_status()
            if is_logged_in:
                logger.info("✅ 登錄狀態驗證成功")
                return True
            else:
                logger.error("❌ 登錄狀態驗證失敗")
                return False
        else:
            logger.error("❌ 登錄失敗")
            return False
    
    async def demonstrate_bank_navigation(self):
        """演示銀行頁面導航"""
        logger.info("\n" + "="*60)
        logger.info("🏦 開始演示銀行頁面導航")
        logger.info("="*60)
        
        # 1. 導航到銀行頁面
        logger.info("1️⃣ 導航到銀行頁面...")
        logger.info(f"銀行頁面URL: {self.settings.bank_url}")
        
        nav_success = await self.bank_operations.navigate_to_bank()
        
        if nav_success:
            logger.info("✅ 成功導航到銀行頁面")
            
            # 2. 檢查當前頁面
            current_url = self.page_navigator.get_current_url()
            page_title = await self.page_navigator.get_page_title()
            
            logger.info(f"當前URL: {current_url}")
            logger.info(f"頁面標題: {page_title}")
            
            return True
        else:
            logger.error("❌ 銀行頁面導航失敗")
            return False
    
    async def demonstrate_bank_information(self):
        """演示銀行信息獲取"""
        logger.info("\n" + "="*60)
        logger.info("💰 開始演示銀行信息獲取")
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
        
        # 3. 計算總可用資金
        logger.info("3️⃣ 計算總可用資金...")
        total_funds = await self.bank_operations.get_total_available_funds()
        if total_funds is not None:
            logger.info(f"✅ 總可用資金: ${total_funds:,}")
        else:
            logger.error("❌ 無法計算總可用資金")
        
        return cash_on_hand, bank_balance, total_funds
    
    async def demonstrate_basic_bank_operations(self):
        """演示基本銀行操作（僅獲取信息，不執行交易）"""
        logger.info("\n" + "="*60)
        logger.info("🔧 開始演示基本銀行操作")
        logger.info("="*60)
        
        # 1. 獲取完整玩家資源
        logger.info("1️⃣ 獲取完整玩家資源...")
        player_resources = await self.bank_operations.get_player_resources()
        
        if player_resources:
            logger.info("✅ 玩家資源獲取成功:")
            logger.info(f"   💵 現金: ${player_resources.cash_on_hand:,}")
            logger.info(f"   🏦 銀行: ${player_resources.bank_balance:,}")
            logger.info(f"   💰 總資金: ${player_resources.total_available_cash:,}")
            logger.info(f"   📦 庫存狀態: {player_resources.inventory_status.current_count}/{player_resources.inventory_status.max_capacity}")
            logger.info(f"   🏪 上架狀態: {player_resources.selling_slots_status.current_listings}/{player_resources.selling_slots_status.max_slots}")
            logger.info(f"   ✅ 可交易: {'是' if player_resources.can_trade else '否'}")
            logger.info(f"   ⚠️ 完全阻塞: {'是' if player_resources.is_completely_blocked else '否'}")
        else:
            logger.error("❌ 無法獲取玩家資源")
        
        return player_resources
    
    async def cleanup(self):
        """清理資源"""
        logger.info("\n🧹 清理資源...")
        
        try:
            if self.browser_manager:
                await self.browser_manager.cleanup()
                logger.info("✅ 瀏覽器管理器已關閉")
                
        except Exception as e:
            logger.error(f"❌ 清理過程中出錯: {e}")
    
    async def run_demo(self):
        """運行簡化演示"""
        logger.info("🎬 開始階段2銀行操作簡化演示")
        logger.info("="*80)
        
        try:
            # 1. 初始化
            if not await self.initialize():
                return False
            
            # 2. 登錄流程演示
            if not await self.demonstrate_login_process():
                return False
            
            # 3. 銀行頁面導航演示
            if not await self.demonstrate_bank_navigation():
                return False
            
            # 4. 銀行信息獲取演示
            await self.demonstrate_bank_information()
            
            # 5. 基本銀行操作演示
            await self.demonstrate_basic_bank_operations()
            
            logger.info("\n" + "="*80)
            logger.info("🎉 階段2銀行操作簡化演示完成！")
            logger.info("="*80)
            
            logger.info("📋 演示功能總結:")
            logger.info("✅ 用戶登錄流程")
            logger.info("✅ 登錄狀態檢查和驗證")
            logger.info("✅ 銀行頁面導航")
            logger.info("✅ 現金餘額獲取")
            logger.info("✅ 銀行餘額獲取")
            logger.info("✅ 總可用資金計算")
            logger.info("✅ 完整玩家資源獲取")
            logger.info("✅ 交易能力評估")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 演示過程中出錯: {e}")
            return False
        
        finally:
            await self.cleanup()


async def main():
    """主函數"""
    demo = Stage2SimpleDemo()
    success = await demo.run_demo()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 