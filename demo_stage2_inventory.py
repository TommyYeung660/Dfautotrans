#!/usr/bin/env python3
"""
Dead Frontier Auto Trading System - Stage 2 Inventory Management Demo
階段2演示：庫存管理模組 - 空間管理和優化
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
from src.dfautotrans.automation.inventory_manager import InventoryManager
from src.dfautotrans.core.page_navigator import PageNavigator
from src.dfautotrans.data.database import DatabaseManager
from src.dfautotrans.core.state_machine import StateMachine


class Stage2InventoryDemo:
    """階段2庫存管理演示"""
    
    def __init__(self):
        self.settings = Settings()
        self.browser_manager = None
        self.login_handler = None
        self.page_navigator = None
        self.bank_operations = None
        self.inventory_manager = None
        self.database_manager = None
        self.state_machine = None
        
    async def initialize(self):
        """初始化所有組件"""
        logger.info("🚀 初始化階段2庫存管理演示系統...")
        
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
            
            # 4. 初始化登錄處理器（包含 Cookie 管理）
            self.login_handler = LoginHandler(
                self.browser_manager, 
                self.page_navigator, 
                self.settings,
                self.database_manager
            )
            logger.info("✅ 登錄處理器初始化完成")
            
            # 5. 初始化銀行操作模組
            self.bank_operations = BankOperations(self.settings, self.browser_manager, self.page_navigator)
            logger.info("✅ 銀行操作模組初始化完成")
            
            # 6. 初始化庫存管理模組
            self.inventory_manager = InventoryManager(self.settings, self.browser_manager, self.page_navigator)
            logger.info("✅ 庫存管理模組初始化完成")
            
            # 7. 初始化狀態機
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
        
        # 1. 確保登錄 - 使用智能登錄
        logger.info("1️⃣ 執行智能登錄...")
        login_success = await self.login_handler.smart_login()
        
        if login_success:
            logger.info("✅ 登錄成功")
        else:
            logger.error("❌ 登錄失敗")
            return False
        
        return True
    
    async def demonstrate_inventory_status_check(self):
        """演示庫存狀態檢查功能"""
        logger.info("\n" + "="*60)
        logger.info("📦 開始演示庫存狀態檢查功能")
        logger.info("="*60)
        
        # 1. 獲取庫存狀態
        logger.info("1️⃣ 檢查庫存狀態...")
        inventory_status = await self.inventory_manager.get_inventory_status()
        if inventory_status:
            logger.info(f"✅ 庫存狀態: {inventory_status.current_count}/{inventory_status.max_capacity}")
            logger.info(f"   可用空間: {inventory_status.available_space}")
            logger.info(f"   使用率: {inventory_status.utilization_rate:.1%}")
            logger.info(f"   是否已滿: {'是' if inventory_status.is_full else '否'}")
        else:
            logger.error("❌ 無法獲取庫存狀態")
        
        # 2. 獲取倉庫狀態
        logger.info("\n2️⃣ 檢查倉庫狀態...")
        storage_status = await self.inventory_manager.get_storage_status()
        if storage_status:
            logger.info(f"✅ 倉庫狀態: {storage_status.current_count}/{storage_status.max_capacity}")
            logger.info(f"   可用空間: {storage_status.available_space}")
            logger.info(f"   使用率: {storage_status.utilization_rate:.1%}")
            logger.info(f"   是否已滿: {'是' if storage_status.is_full else '否'}")
        else:
            logger.error("❌ 無法獲取倉庫狀態")
        
        # 3. 獲取銷售位狀態
        logger.info("\n3️⃣ 檢查銷售位狀態...")
        selling_status = await self.inventory_manager.get_selling_slots_status()
        if selling_status:
            logger.info(f"✅ 銷售位狀態: {selling_status.current_listings}/{selling_status.max_slots}")
            logger.info(f"   可用位置: {selling_status.available_slots}")
            logger.info(f"   使用率: {selling_status.current_listings/selling_status.max_slots:.1%}")
            logger.info(f"   是否已滿: {'是' if selling_status.is_full else '否'}")
        else:
            logger.error("❌ 無法獲取銷售位狀態")
        
        return inventory_status, storage_status, selling_status
    
    async def demonstrate_inventory_items_retrieval(self):
        """演示庫存物品檢索功能"""
        logger.info("\n" + "="*60)
        logger.info("📋 開始演示庫存物品檢索功能")
        logger.info("="*60)
        
        # 1. 獲取庫存物品列表
        logger.info("1️⃣ 獲取庫存物品列表...")
        inventory_items = await self.inventory_manager.get_inventory_items()
        
        if inventory_items:
            logger.info(f"✅ 找到 {len(inventory_items)} 件庫存物品:")
            for i, item in enumerate(inventory_items[:10], 1):  # 只顯示前10件
                logger.info(f"   {i}. {item}")
            
            if len(inventory_items) > 10:
                logger.info(f"   ... 和其他 {len(inventory_items) - 10} 件物品")
        else:
            logger.info("ℹ️ 庫存中沒有物品或無法獲取物品列表")
        
        return inventory_items
    
    async def demonstrate_space_management(self, inventory_status):
        """演示空間管理功能"""
        logger.info("\n" + "="*60)
        logger.info("🎯 開始演示空間管理功能")
        logger.info("="*60)
        
        # 1. 檢查庫存是否已滿
        logger.info("1️⃣ 檢查庫存空間狀況...")
        is_full = await self.inventory_manager.check_inventory_full()
        logger.info(f"   庫存是否已滿: {'是' if is_full else '否'}")
        
        # 2. 模擬空間需求計算
        logger.info("\n2️⃣ 模擬空間需求計算...")
        mock_market_items = [
            {"name": "Pistol", "quantity": 1},
            {"name": "Ammo", "quantity": 5},
            {"name": "Medicine", "quantity": 2}
        ]
        
        required_space = await self.inventory_manager.calculate_space_requirements(mock_market_items)
        logger.info(f"   模擬購買物品需要空間: {required_space}")
        
        has_space = await self.inventory_manager.has_sufficient_space(required_space)
        logger.info(f"   是否有足夠空間: {'是' if has_space else '否'}")
        
        # 3. 演示庫存空間優化
        logger.info("\n3️⃣ 演示庫存空間優化...")
        optimization_result = await self.inventory_manager.optimize_inventory_space()
        
        if optimization_result:
            logger.info("✅ 庫存空間優化完成")
            
            # 重新檢查庫存狀態
            logger.info("   重新檢查庫存狀態...")
            new_inventory_status = await self.inventory_manager.get_inventory_status()
            if new_inventory_status:
                logger.info(f"   優化後庫存: {new_inventory_status.current_count}/{new_inventory_status.max_capacity}")
                
                if inventory_status:
                    space_freed = inventory_status.current_count - new_inventory_status.current_count
                    if space_freed > 0:
                        logger.info(f"   釋放了 {space_freed} 個空間")
                    else:
                        logger.info("   庫存狀態無變化（可能原本就未滿）")
        else:
            logger.warning("⚠️ 庫存空間優化未完成")
        
        return optimization_result
    
    async def demonstrate_storage_operations(self):
        """演示存儲操作功能"""
        logger.info("\n" + "="*60)
        logger.info("🏪 開始演示存儲操作功能")
        logger.info("="*60)
        
        # 1. 獲取操作前的狀態
        logger.info("1️⃣ 獲取操作前的狀態...")
        initial_inventory = await self.inventory_manager.get_inventory_status()
        initial_storage = await self.inventory_manager.get_storage_status()
        
        if initial_inventory:
            logger.info(f"   操作前庫存: {initial_inventory.current_count}/{initial_inventory.max_capacity}")
        if initial_storage:
            logger.info(f"   操作前倉庫: {initial_storage.current_count}/{initial_storage.max_capacity}")
        
        # 2. 測試存入所有物品到倉庫
        if initial_inventory and initial_inventory.current_count > 0:
            logger.info("\n2️⃣ 測試存入所有物品到倉庫...")
            
            deposit_result = await self.inventory_manager.deposit_all_to_storage()
            
            if deposit_result:
                logger.info("✅ 存入操作執行成功")
                
                # 驗證結果
                logger.info("   驗證操作結果...")
                final_inventory = await self.inventory_manager.get_inventory_status()
                final_storage = await self.inventory_manager.get_storage_status()
                
                if final_inventory:
                    logger.info(f"   操作後庫存: {final_inventory.current_count}/{final_inventory.max_capacity}")
                    
                    if initial_inventory.current_count > final_inventory.current_count:
                        moved_items = initial_inventory.current_count - final_inventory.current_count
                        logger.info(f"   ✅ 成功轉移了 {moved_items} 件物品到倉庫")
                    else:
                        logger.info("   ℹ️ 庫存物品數量無變化")
                
                if final_storage:
                    logger.info(f"   操作後倉庫: {final_storage.current_count}/{final_storage.max_capacity}")
                    
                    if initial_storage and final_storage.current_count > initial_storage.current_count:
                        received_items = final_storage.current_count - initial_storage.current_count
                        logger.info(f"   ✅ 倉庫接收了 {received_items} 件物品")
                        
            else:
                logger.error("❌ 存入操作執行失敗")
        else:
            logger.info("2️⃣ 庫存中沒有物品，跳過存入操作演示")
        
        # 3. 測試從倉庫取出所有物品
        if initial_storage and initial_storage.current_count > 0:
            logger.info("\n3️⃣ 測試從倉庫取出所有物品...")
            
            withdraw_result = await self.inventory_manager.withdraw_all_from_storage()
            
            if withdraw_result:
                logger.info("✅ 取出操作執行成功")
                
                # 驗證結果
                logger.info("   驗證操作結果...")
                final_inventory_2 = await self.inventory_manager.get_inventory_status()
                final_storage_2 = await self.inventory_manager.get_storage_status()
                
                if final_storage_2:
                    logger.info(f"   操作後倉庫: {final_storage_2.current_count}/{final_storage_2.max_capacity}")
                
                if final_inventory_2:
                    logger.info(f"   操作後庫存: {final_inventory_2.current_count}/{final_inventory_2.max_capacity}")
                        
            else:
                logger.error("❌ 取出操作執行失敗")
        else:
            logger.info("3️⃣ 倉庫中沒有物品，跳過取出操作演示")
        
        return initial_inventory, initial_storage
    
    async def demonstrate_integrated_resource_management(self):
        """演示整合資源管理功能"""
        logger.info("\n" + "="*60)
        logger.info("🎯 開始演示整合資源管理功能")
        logger.info("="*60)
        
        # 1. 獲取完整的玩家資源狀況
        logger.info("1️⃣ 獲取完整玩家資源狀況...")
        
        # 從銀行操作獲取資金信息
        player_resources = await self.bank_operations.get_player_resources()
        if player_resources:
            logger.info("✅ 完整玩家資源:")
            logger.info(f"   💰 現金: ${player_resources.cash_on_hand:,}")
            logger.info(f"   🏦 銀行: ${player_resources.bank_balance:,}")
            logger.info(f"   💵 總資金: ${player_resources.total_available_cash:,}")
            logger.info(f"   📦 庫存: {player_resources.inventory_status.current_count}/{player_resources.inventory_status.max_capacity}")
            logger.info(f"   🏪 倉庫: {player_resources.storage_status.current_count}/{player_resources.storage_status.max_capacity}")
            logger.info(f"   🛒 銷售位: {player_resources.selling_slots_status.current_listings}/{player_resources.selling_slots_status.max_slots}")
            logger.info(f"   ✅ 可交易: {'是' if player_resources.can_trade else '否'}")
            logger.info(f"   🚫 完全阻塞: {'是' if player_resources.is_completely_blocked else '否'}")
        else:
            logger.error("❌ 無法獲取完整玩家資源")
        
        # 2. 演示交易能力評估
        logger.info("\n2️⃣ 演示交易能力評估...")
        
        # 模擬購買需求
        mock_purchase_requirements = {
            "required_cash": 10000,
            "required_space": 5
        }
        
        # 檢查資金是否足夠
        has_funds = player_resources and player_resources.total_available_cash >= mock_purchase_requirements["required_cash"]
        logger.info(f"   資金充足性: {'✅ 充足' if has_funds else '❌ 不足'}")
        
        # 檢查空間是否足夠
        has_space = await self.inventory_manager.has_sufficient_space(mock_purchase_requirements["required_space"])
        logger.info(f"   空間充足性: {'✅ 充足' if has_space else '❌ 不足'}")
        
        # 綜合評估
        can_trade = has_funds and has_space
        logger.info(f"   交易能力: {'✅ 可以交易' if can_trade else '❌ 暫時無法交易'}")
        
        if not can_trade:
            logger.info("   建議操作:")
            if not has_funds:
                logger.info("     - 從銀行提取資金")
            if not has_space:
                logger.info("     - 清理庫存空間")
        
        return player_resources
    
    async def cleanup(self):
        """清理資源"""
        logger.info("\n🧹 開始清理資源...")
        
        try:
            if self.browser_manager:
                await self.browser_manager.cleanup()
                logger.info("✅ 瀏覽器管理器已清理")
            
            if self.database_manager:
                await self.database_manager.close()
                logger.info("✅ 數據庫管理器已清理")
                
        except Exception as e:
            logger.error(f"⚠️ 清理過程中出錯: {e}")
    
    async def run_full_demo(self):
        """運行完整演示"""
        try:
            logger.info("🎬 開始階段2庫存管理完整演示")
            logger.info("=" * 80)
            
            # 初始化系統
            if not await self.initialize():
                logger.error("❌ 系統初始化失敗")
                return
            
            # 登錄和導航
            if not await self.demonstrate_login_and_navigation():
                logger.error("❌ 登錄演示失敗")
                return
            
            # 庫存狀態檢查
            inventory_status, storage_status, selling_status = await self.demonstrate_inventory_status_check()
            
            # 庫存物品檢索
            inventory_items = await self.demonstrate_inventory_items_retrieval()
            
            # 空間管理
            await self.demonstrate_space_management(inventory_status)
            
            # 存儲操作
            await self.demonstrate_storage_operations()
            
            # 整合資源管理
            await self.demonstrate_integrated_resource_management()
            
            logger.info("\n" + "="*80)
            logger.info("🎉 階段2庫存管理演示完成！")
            logger.info("主要功能驗證:")
            logger.info("✅ 庫存狀態檢查")
            logger.info("✅ 倉庫狀態檢查")
            logger.info("✅ 銷售位狀態檢查")
            logger.info("✅ 庫存物品檢索")
            logger.info("✅ 空間管理和優化")
            logger.info("✅ 存儲操作")
            logger.info("✅ 整合資源管理")
            logger.info("🚀 準備進入階段3開發")
            logger.info("="*80)
            
        except Exception as e:
            logger.error(f"❌ 演示過程中發生錯誤: {e}")
        finally:
            await self.cleanup()


async def main():
    """主函數"""
    demo = Stage2InventoryDemo()
    await demo.run_full_demo()


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