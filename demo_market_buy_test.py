#!/usr/bin/env python3
"""
市場購買功能測試演示
搜索 12.7mm Rifle Bullets 並購買所有單價 <= 11.67 的貨品
"""

import asyncio
import sys
from pathlib import Path

# 添加項目根目錄到Python路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from loguru import logger
from src.dfautotrans.config.settings import Settings
from src.dfautotrans.automation.browser_manager import BrowserManager
from src.dfautotrans.automation.login_handler import LoginHandler
from src.dfautotrans.automation.market_operations import MarketOperations
from src.dfautotrans.core.page_navigator import PageNavigator
from src.dfautotrans.data.database import DatabaseManager


async def test_market_buy_functionality():
    """測試市場購買功能"""
    
    # 初始化組件
    settings = Settings()
    browser_manager = BrowserManager(settings)
    database_manager = DatabaseManager(settings)
    page_navigator = PageNavigator(browser_manager, settings)
    login_handler = LoginHandler(browser_manager, page_navigator, settings, database_manager)
    market_operations = MarketOperations(settings, browser_manager, page_navigator)
    
    # 購買參數
    target_item = "12.7mm Rifle Bullets"
    max_price_per_unit = 11.67
    
    try:
        logger.info("🚀 開始市場購買功能測試")
        logger.info("=" * 60)
        logger.info(f"🎯 目標物品: {target_item}")
        logger.info(f"💰 最大單價: ${max_price_per_unit}")
        logger.info("=" * 60)
        
        # 初始化系統
        logger.info("🔧 初始化瀏覽器管理器...")
        await browser_manager.initialize()
        
        logger.info("🔧 初始化頁面導航器...")
        await page_navigator.initialize()
        
        # 智能登錄
        logger.info("🔐 執行智能登錄...")
        login_success = await login_handler.smart_login()
        
        if not login_success:
            logger.error("❌ 登錄失敗，無法繼續測試")
            return False
        
        logger.info("✅ 登錄成功！")
        
        # 獲取初始資金
        initial_cash = await page_navigator.get_current_cash()
        logger.info(f"💰 初始資金: ${initial_cash:,}" if initial_cash else "💰 無法獲取初始資金")
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("🔍 開始搜索目標物品")
        logger.info("=" * 60)
        
        # 搜索目標物品
        logger.info(f"🔍 搜索物品: {target_item}...")
        market_items = await market_operations.scan_market_items(
            search_term=target_item, 
            max_items=50  # 增加掃描數量
        )
        
        if not market_items:
            logger.warning("⚠️ 沒有找到任何物品")
            return False
        
        logger.info(f"✅ 找到 {len(market_items)} 個 {target_item}")
        
        # 篩選符合價格條件的物品
        affordable_items = [
            item for item in market_items 
            if item.price <= max_price_per_unit
        ]
        
        if not affordable_items:
            logger.warning(f"⚠️ 沒有找到單價 <= ${max_price_per_unit} 的物品")
            logger.info("📊 所有物品價格:")
            for i, item in enumerate(market_items[:10], 1):
                logger.info(f"   {i}. {item.item_name} - ${item.price}/單位 ({item.seller})")
            return False
        
        logger.info(f"✅ 找到 {len(affordable_items)} 個符合價格條件的物品")
        logger.info("📊 符合條件的物品:")
        total_cost = 0
        for i, item in enumerate(affordable_items, 1):
            item_total_cost = item.price * item.quantity
            total_cost += item_total_cost
            logger.info(f"   {i}. {item.item_name} - ${item.price}/單位 x{item.quantity} = ${item_total_cost:.2f} ({item.seller})")
        
        logger.info(f"💰 總購買成本: ${total_cost:.2f}")
        
        # 檢查資金是否足夠
        if initial_cash and total_cost > initial_cash:
            logger.warning(f"⚠️ 資金不足！需要 ${total_cost:.2f}，但只有 ${initial_cash:,}")
            logger.info("📊 將按價格排序購買，直到資金用完")
            # 按價格排序，優先購買便宜的
            affordable_items.sort(key=lambda x: x.price)
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("💰 開始執行購買操作")
        logger.info("=" * 60)
        
        # 執行購買
        successful_purchases = 0
        failed_purchases = 0
        total_spent = 0
        
        for i, item in enumerate(affordable_items, 1):
            item_cost = item.price * item.quantity
            
            # 檢查剩餘資金
            if initial_cash and (total_spent + item_cost) > initial_cash:
                logger.warning(f"⚠️ 跳過物品 {i}: 資金不足")
                continue
            
            logger.info(f"🛒 購買物品 {i}/{len(affordable_items)}: {item.item_name}")
            logger.info(f"   💰 價格: ${item.price}/單位 x{item.quantity} = ${item_cost:.2f}")
            logger.info(f"   👤 賣家: {item.seller}")
            
            # 執行購買
            purchase_success = await market_operations.execute_purchase(item)
            
            if purchase_success:
                successful_purchases += 1
                total_spent += item_cost
                logger.info(f"   ✅ 購買成功！")
            else:
                failed_purchases += 1
                logger.info(f"   ❌ 購買失敗")
            
            # 短暫延遲避免過快操作
            await asyncio.sleep(2)
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("📊 購買結果統計")
        logger.info("=" * 60)
        logger.info(f"✅ 成功購買: {successful_purchases} 個物品")
        logger.info(f"❌ 購買失敗: {failed_purchases} 個物品")
        logger.info(f"💰 總花費: ${total_spent:.2f}")
        
        # 獲取最終資金
        final_cash = await page_navigator.get_current_cash()
        if final_cash and initial_cash:
            actual_spent = initial_cash - final_cash
            logger.info(f"💰 最終資金: ${final_cash:,}")
            logger.info(f"💸 實際花費: ${actual_spent:,}")
            
            if abs(actual_spent - total_spent) > 1:  # 允許小誤差
                logger.warning(f"⚠️ 計算花費與實際花費不符！")
        
        logger.info("")
        if successful_purchases > 0:
            logger.info("🎉 購買測試完成！有成功購買的物品")
            return True
        else:
            logger.warning("⚠️ 購買測試完成，但沒有成功購買任何物品")
            return False
        
    except Exception as e:
        logger.error(f"❌ 測試過程中出現錯誤: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # 清理資源
        try:
            if hasattr(browser_manager, 'close'):
                await browser_manager.close()
            logger.info("🧹 瀏覽器資源已清理")
        except Exception as e:
            logger.warning(f"清理瀏覽器資源時出錯: {e}")


async def main():
    """主函數"""
    try:
        success = await test_market_buy_functionality()
        
        if success:
            logger.info("🎯 市場購買功能測試成功！")
            return 0
        else:
            logger.error("❌ 測試失敗")
            return 1
            
    except KeyboardInterrupt:
        logger.info("🛑 用戶中斷測試")
        return 0
    except Exception as e:
        logger.error(f"❌ 程序執行錯誤: {e}")
        return 1


if __name__ == "__main__":
    # 配置日誌
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}")
    
    # 運行測試
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 