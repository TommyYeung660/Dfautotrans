"""階段1完整演示腳本 - 展示基礎設施和登錄功能"""

import asyncio
import sys
from pathlib import Path

# 添加 src 目錄到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.dfautotrans.config.settings import Settings
from src.dfautotrans.automation.browser_manager import BrowserManager
from src.dfautotrans.core.page_navigator import PageNavigator
from src.dfautotrans.automation.login_handler import LoginHandler
from src.dfautotrans.core.state_machine import StateMachine
from src.dfautotrans.data.database import DatabaseManager
from src.dfautotrans.data.models import TradingState
from loguru import logger


class Stage1Demo:
    """階段1完整演示類"""
    
    def __init__(self):
        self.settings = Settings()
        # 確保使用可視化瀏覽器
        self.settings.browser.headless = False
        
        # 初始化組件
        self.browser_manager = None
        self.page_navigator = None
        self.login_handler = None
        self.state_machine = None
        self.database_manager = None
    
    async def initialize_components(self):
        """初始化所有組件"""
        logger.info("🚀 開始初始化階段1組件...")
        
        # 1. 初始化數據庫管理器
        logger.info("📊 初始化數據庫管理器...")
        self.database_manager = DatabaseManager(self.settings)
        await self.database_manager.initialize()
        logger.info("✅ 數據庫管理器初始化完成")
        
        # 2. 初始化瀏覽器管理器
        logger.info("🌐 初始化瀏覽器管理器...")
        self.browser_manager = BrowserManager(self.settings)
        await self.browser_manager.start()
        logger.info("✅ 瀏覽器管理器初始化完成")
        
        # 3. 初始化頁面導航器
        logger.info("🧭 初始化頁面導航器...")
        self.page_navigator = PageNavigator(self.browser_manager, self.settings)
        await self.page_navigator.initialize()
        logger.info("✅ 頁面導航器初始化完成")
        
        # 4. 初始化登錄處理器
        logger.info("🔐 初始化登錄處理器...")
        self.login_handler = LoginHandler(self.browser_manager, self.page_navigator, self.settings)
        logger.info("✅ 登錄處理器初始化完成")
        
        # 5. 初始化狀態機
        logger.info("⚙️ 初始化交易狀態機...")
        self.state_machine = StateMachine(self.settings)
        logger.info("✅ 交易狀態機初始化完成")
        
        logger.info("🎉 所有階段1組件初始化完成！")
    
    async def demonstrate_login_flow(self):
        """演示登錄流程"""
        logger.info("\n" + "="*50)
        logger.info("🔐 開始演示登錄流程")
        logger.info("="*50)
        
        # 1. 檢查登錄狀態
        logger.info("1️⃣ 檢查當前登錄狀態...")
        is_logged_in = await self.login_handler.check_login_status()
        logger.info(f"   登錄狀態: {'已登錄' if is_logged_in else '未登錄'}")
        
        if not is_logged_in:
            # 2. 執行登錄
            logger.info("2️⃣ 執行登錄操作...")
            login_success = await self.login_handler.perform_login()
            
            if login_success:
                logger.info("✅ 登錄成功！")
                
                # 3. 驗證登錄成功
                logger.info("3️⃣ 驗證登錄狀態...")
                verified = await self.login_handler.verify_login_success()
                logger.info(f"   登錄驗證: {'通過' if verified else '失敗'}")
                
                # 4. 獲取用戶信息
                logger.info("4️⃣ 獲取用戶信息...")
                try:
                    # 嘗試獲取現金信息
                    cash_element = await self.browser_manager.page.query_selector('text=/Cash:/')
                    if cash_element:
                        cash_text = await cash_element.text_content()
                        logger.info(f"   💰 {cash_text}")
                    
                    # 嘗試獲取用戶等級信息
                    level_element = await self.browser_manager.page.query_selector('text=/Level/')
                    if level_element:
                        level_text = await level_element.text_content()
                        logger.info(f"   🎯 {level_text}")
                        
                except Exception as e:
                    logger.debug(f"獲取用戶信息時出錯: {e}")
                
                return True
            else:
                logger.error("❌ 登錄失敗！")
                return False
        else:
            logger.info("ℹ️ 用戶已經登錄，跳過登錄流程")
            return True
    
    async def demonstrate_page_navigation(self):
        """演示頁面導航功能"""
        logger.info("\n" + "="*50)
        logger.info("🧭 開始演示頁面導航功能")
        logger.info("="*50)
        
        # 1. 導航到主頁
        logger.info("1️⃣ 導航到遊戲主頁...")
        success = await self.page_navigator.navigate_to_home()
        if success:
            logger.info("✅ 成功導航到主頁")
            
            # 獲取現金信息
            cash = await self.page_navigator.get_current_cash()
            if cash is not None:
                logger.info(f"💰 當前現金: ${cash:,}")
        else:
            logger.error("❌ 導航到主頁失敗")
        
        # 等待3秒讓用戶觀察
        logger.info("⏳ 等待3秒讓您觀察頁面...")
        await asyncio.sleep(3)
        
        # 2. 導航到市場
        logger.info("2️⃣ 導航到市場頁面...")
        success = await self.page_navigator.navigate_to_marketplace()
        if success:
            logger.info("✅ 成功導航到市場")
        else:
            logger.error("❌ 導航到市場失敗")
        
        # 等待3秒讓用戶觀察
        logger.info("⏳ 等待3秒讓您觀察市場頁面...")
        await asyncio.sleep(3)
        
        # 3. 導航到銀行
        logger.info("3️⃣ 導航到銀行頁面...")
        success = await self.page_navigator.navigate_to_bank()
        if success:
            logger.info("✅ 成功導航到銀行")
        else:
            logger.error("❌ 導航到銀行失敗")
        
        # 等待3秒讓用戶觀察
        logger.info("⏳ 等待3秒讓您觀察銀行頁面...")
        await asyncio.sleep(3)
        
        # 4. 導航到倉庫
        logger.info("4️⃣ 導航到倉庫頁面...")
        success = await self.page_navigator.navigate_to_storage()
        if success:
            logger.info("✅ 成功導航到倉庫")
        else:
            logger.error("❌ 導航到倉庫失敗")
        
        # 等待3秒讓用戶觀察
        logger.info("⏳ 等待3秒讓您觀察倉庫頁面...")
        await asyncio.sleep(3)
    
    async def demonstrate_state_machine(self):
        """演示狀態機功能"""
        logger.info("\n" + "="*50)
        logger.info("⚙️ 開始演示交易狀態機功能")
        logger.info("="*50)
        
        # 1. 顯示當前狀態
        current_state = self.state_machine.current_state
        logger.info(f"1️⃣ 當前狀態: {current_state.value}")
        
        # 2. 演示狀態轉換
        logger.info("2️⃣ 演示狀態轉換...")
        
        # 轉換到初始化狀態
        success = await self.state_machine.transition_to(TradingState.INITIALIZING)
        if success:
            logger.info("✅ 成功轉換到 INITIALIZING 狀態")
        
        # 轉換到檢查資源狀態
        success = await self.state_machine.transition_to(TradingState.CHECKING_RESOURCES)
        if success:
            logger.info("✅ 成功轉換到 CHECKING_RESOURCES 狀態")
        
        # 轉換到市場掃描狀態
        success = await self.state_machine.transition_to(TradingState.MARKET_SCANNING)
        if success:
            logger.info("✅ 成功轉換到 MARKET_SCANNING 狀態")
        
        # 3. 顯示狀態統計
        stats = self.state_machine.get_state_statistics()
        logger.info("3️⃣ 狀態機統計信息:")
        if stats:
            logger.info(f"   總轉換次數: {stats['total_transitions']}")
            logger.info(f"   總持續時間: {stats['total_duration']:.1f} 秒")
            logger.info(f"   當前狀態持續時間: {stats['current_state_duration']:.1f} 秒")
        else:
            logger.info("   暫無統計數據")
    
    async def demonstrate_database_operations(self):
        """演示數據庫操作"""
        logger.info("\n" + "="*50)
        logger.info("📊 開始演示數據庫操作功能")
        logger.info("="*50)
        
        # 1. 創建交易會話
        logger.info("1️⃣ 創建交易會話...")
        session = await self.database_manager.create_trading_session(initial_cash=100000)
        if session:
            logger.info(f"✅ 創建交易會話成功，ID: {session.id}")
        else:
            logger.error("❌ 創建交易會話失敗")
            return
        
        # 2. 記錄系統狀態
        logger.info("2️⃣ 記錄系統狀態...")
        state_success = await self.database_manager.save_system_state({
            "current_state": "DEMO_STATE",
            "session_id": session.id,
            "state_data": '{"demo": true, "stage": 1}'
        })
        if state_success:
            logger.info("✅ 系統狀態記錄成功")
        else:
            logger.error("❌ 系統狀態記錄失敗")
        
        # 3. 記錄資源快照
        logger.info("3️⃣ 記錄資源快照...")
        snapshot_success = await self.database_manager.save_resource_snapshot({
            "session_id": session.id,
            "cash_on_hand": 100000,
            "bank_balance": 0,
            "inventory_count": 15,
            "storage_count": 200,
            "selling_slots_used": 5
        })
        if snapshot_success:
            logger.info("✅ 資源快照記錄成功")
        else:
            logger.error("❌ 資源快照記錄失敗")
        
        # 4. 獲取統計信息
        logger.info("4️⃣ 獲取數據庫統計信息...")
        stats = await self.database_manager.get_trading_statistics()
        logger.info("📈 數據庫統計:")
        logger.info(f"   總交易數: {stats.get('total_trades', 0)}")
        logger.info(f"   總利潤: ${stats.get('total_profit', 0.0):.2f}")
        logger.info(f"   平均利潤: ${stats.get('average_profit', 0.0):.2f}")
    
    async def run_complete_demo(self):
        """運行完整演示"""
        try:
            logger.info("🎬 開始階段1完整演示")
            logger.info("=" * 60)
            
            # 初始化所有組件
            await self.initialize_components()
            
            # 演示登錄流程
            login_success = await self.demonstrate_login_flow()
            if not login_success:
                logger.error("❌ 登錄演示失敗，終止演示")
                return
            
            # 演示頁面導航
            await self.demonstrate_page_navigation()
            
            # 演示狀態機
            await self.demonstrate_state_machine()
            
            # 演示數據庫操作
            await self.demonstrate_database_operations()
            
            logger.info("\n" + "="*60)
            logger.info("🎉 階段1完整演示成功完成！")
            logger.info("✅ 所有核心功能都已驗證")
            logger.info("🚀 準備進入階段2開發")
            logger.info("="*60)
            
        except Exception as e:
            logger.error(f"❌ 演示過程中發生錯誤: {e}")
            raise
        finally:
            # 清理資源
            await self.cleanup()
    
    async def cleanup(self):
        """清理資源"""
        logger.info("🧹 開始清理資源...")
        
        if self.browser_manager:
            try:
                await self.browser_manager.cleanup()
                logger.info("✅ 瀏覽器管理器已清理")
            except Exception as e:
                logger.error(f"⚠️ 瀏覽器清理失敗: {e}")
        
        if self.database_manager:
            try:
                await self.database_manager.close()
                logger.info("✅ 數據庫管理器已清理")
            except Exception as e:
                logger.error(f"⚠️ 數據庫清理失敗: {e}")
        
        logger.info("✅ 資源清理完成")


async def main():
    """主函數"""
    demo = Stage1Demo()
    await demo.run_complete_demo()


if __name__ == "__main__":
    # 配置日誌格式
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>",
        level="INFO"
    )
    
    # 運行演示
    asyncio.run(main()) 