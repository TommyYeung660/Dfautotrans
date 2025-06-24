#!/usr/bin/env python3
"""
Debug script for withdraw from storage functionality
檢查從倉庫取出功能的實現
"""

import asyncio
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dfautotrans.automation.browser_manager import BrowserManager
from dfautotrans.automation.login_handler import LoginHandler
from dfautotrans.automation.inventory_manager import InventoryManager
from dfautotrans.core.page_navigator import PageNavigator
from dfautotrans.config.settings import Settings
from dfautotrans.utils.logger import get_logger

logger = get_logger(__name__)

async def main():
    """測試從倉庫取出功能"""
    browser_manager = None
    
    try:
        logger.info("=== 開始測試從倉庫取出功能 ===")
        
        # 1. 初始化設定
        settings = Settings()
        
        # 2. 啟動瀏覽器
        browser_manager = BrowserManager(settings)
        await browser_manager.start()
        page = browser_manager.page
        
        # 3. 執行登錄
        page_navigator = PageNavigator(page, settings)
        login_handler = LoginHandler(browser_manager, page_navigator, settings)
        if not await login_handler.smart_login():
            logger.error("登錄失敗")
            return False
            
        # 4. 初始化庫存管理器
        inventory_manager = InventoryManager(settings, browser_manager, page_navigator)
        
        # 5. 獲取初始狀態
        logger.info("📊 獲取初始狀態...")
        
        inventory_status = await inventory_manager.get_inventory_status()
        storage_status = await inventory_manager.get_storage_status()
        
        logger.info(f"庫存狀態: {inventory_status['used']}/{inventory_status['total']}")
        logger.info(f"倉庫狀態: {storage_status['used']}/{storage_status['total']}")
        
        if storage_status['used'] == 0:
            logger.info("倉庫為空，先從庫存存入一些物品到倉庫進行測試")
            if inventory_status['used'] > 0:
                logger.info("嘗試將庫存物品存入倉庫...")
                if await inventory_manager.deposit_all_to_storage():
                    logger.info("✅ 成功存入物品到倉庫")
                    # 重新獲取狀態
                    storage_status = await inventory_manager.get_storage_status()
                    logger.info(f"更新後倉庫狀態: {storage_status['used']}/{storage_status['total']}")
                else:
                    logger.error("❌ 存入倉庫失敗")
                    return False
            else:
                logger.warning("庫存和倉庫都為空，無法進行測試")
                return False
        
        # 6. 測試從倉庫取出功能
        logger.info("🔄 開始測試從倉庫取出功能...")
        
        if await inventory_manager.withdraw_all_from_storage():
            logger.info("✅ 從倉庫取出功能測試成功")
            
            # 驗證結果
            new_inventory = await inventory_manager.get_inventory_status()
            new_storage = await inventory_manager.get_storage_status()
            
            logger.info(f"操作後庫存狀態: {new_inventory['used']}/{new_inventory['total']}")
            logger.info(f"操作後倉庫狀態: {new_storage['used']}/{new_storage['total']}")
            
            return True
        else:
            logger.error("❌ 從倉庫取出功能測試失敗")
            return False
            
    except Exception as e:
        logger.error(f"測試過程中發生錯誤: {e}")
        return False
        
    finally:
        if browser_manager:
            await browser_manager.cleanup()

if __name__ == "__main__":
    success = asyncio.run(main())
    if success:
        logger.info("🎉 所有測試通過!")
        sys.exit(0)
    else:
        logger.error("❌ 測試失敗!")
        sys.exit(1) 