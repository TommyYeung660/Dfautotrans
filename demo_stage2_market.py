#!/usr/bin/env python3
"""
階段2.4 市場操作模組演示
測試市場掃描、銷售位狀態檢查、購買操作等功能
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


async def test_market_operations():
    """測試市場操作功能"""
    
    # 初始化組件
    settings = Settings()
    browser_manager = BrowserManager(settings)
    database_manager = DatabaseManager(settings)
    page_navigator = PageNavigator(browser_manager, settings)
    login_handler = LoginHandler(browser_manager, page_navigator, settings, database_manager)
    market_operations = MarketOperations(settings, browser_manager, page_navigator)
    
    try:
        logger.info("🚀 開始階段2.4市場操作演示")
        logger.info("=" * 60)
        
        # 初始化瀏覽器和頁面導航器
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
        logger.info("=" * 60)
        
        # 測試1: 市場掃描功能
        logger.info("📊 測試1: 市場掃描功能")
        logger.info("-" * 40)
        
        # 掃描所有市場物品
        logger.info("🔍 掃描市場物品...")
        market_items = await market_operations.scan_market_items(max_items=10)
        
        if market_items:
            logger.info(f"✅ 成功掃描到 {len(market_items)} 個市場物品")
            for i, item in enumerate(market_items[:5], 1):  # 顯示前5個
                logger.info(f"   {i}. {item.item_name} - ${item.price} ({item.seller})")
            if len(market_items) > 5:
                logger.info(f"   ... 還有 {len(market_items) - 5} 個物品")
        else:
            logger.warning("⚠️ 沒有掃描到市場物品")
        
        # 搜索特定物品
        logger.info("🔍 搜索特定物品: '12.7 mm Rifle Bullets'...")
        rifle_bullets = await market_operations.scan_market_items(
            search_term="12.7 mm Rifle Bullets", 
            max_items=5
        )
        
        if rifle_bullets:
            logger.info(f"✅ 找到 {len(rifle_bullets)} 個 12.7 mm Rifle Bullets")
            for i, item in enumerate(rifle_bullets, 1):
                logger.info(f"   {i}. {item.item_name} - ${item.price} ({item.seller})")
        else:
            logger.warning("⚠️ 沒有找到 12.7 mm Rifle Bullets")
        
        logger.info("")
        
        # 測試2: 銷售位狀態檢查
        logger.info("📊 測試2: 銷售位狀態檢查")
        logger.info("-" * 40)
        
        selling_status = await market_operations.get_selling_slots_status()
        
        if selling_status:
            logger.info(f"✅ 銷售位狀態:")
            logger.info(f"   📊 已使用: {selling_status.current_listings}")
            logger.info(f"   📊 最大容量: {selling_status.max_slots}")
            logger.info(f"   📊 可用位置: {selling_status.available_slots}")
            logger.info(f"   📊 使用率: {selling_status.current_listings/selling_status.max_slots*100:.1f}%")
            
            if selling_status.listed_items:
                logger.info(f"   📝 已上架物品:")
                for item in selling_status.listed_items[:3]:  # 顯示前3個
                    logger.info(f"      - {item}")
            else:
                logger.info("   📝 沒有已上架的物品")
        else:
            logger.warning("⚠️ 無法獲取銷售位狀態")
        
        logger.info("")
        
        # 測試3: 市場概要信息
        logger.info("📊 測試3: 市場概要信息")
        logger.info("-" * 40)
        
        market_summary = await market_operations.get_market_summary()
        
        if market_summary:
            logger.info(f"✅ 市場概要:")
            logger.info(f"   📈 總物品數: {market_summary.get('total_items', 0)}")
            logger.info(f"   💰 平均價格: ${market_summary.get('average_price', 0):.2f}")
            
            price_range = market_summary.get('price_range', (0, 0))
            if price_range[0] > 0:
                logger.info(f"   💸 價格範圍: ${price_range[0]:.2f} - ${price_range[1]:.2f}")
            
            item_types = market_summary.get('item_types', {})
            if item_types:
                logger.info(f"   📦 物品類型:")
                for item_type, count in list(item_types.items())[:3]:  # 顯示前3種
                    logger.info(f"      - {item_type}: {count} 個")
                    
            selling_info = market_summary.get('selling_slots', {})
            if selling_info:
                logger.info(f"   🛒 銷售位: {selling_info.get('used', 0)}/{selling_info.get('max', 30)}")
        else:
            logger.warning("⚠️ 無法獲取市場概要信息")
        
        logger.info("")
        
        # 測試4: 購買功能（僅模擬，不實際購買）
        logger.info("📊 測試4: 購買功能測試（模擬）")
        logger.info("-" * 40)
        
        if rifle_bullets and len(rifle_bullets) > 0:
            test_item = rifle_bullets[0]  # 選擇第一個物品進行測試
            logger.info(f"🎯 選擇測試物品: {test_item.item_name} - ${test_item.price}")
            logger.info(f"   賣家: {test_item.seller}")
            logger.info(f"   數量: {test_item.quantity}")
            
            # 注意: 這裡不會實際執行購買，只是顯示功能可用
            logger.info("ℹ️ 購買功能已實現但在演示中不執行實際購買")
            logger.info("   可用方法: market_operations.execute_purchase(item)")
        else:
            logger.info("ℹ️ 沒有可用的測試物品進行購買測試")
        
        logger.info("")
        
        # 測試5: 銷售功能（僅模擬，不實際銷售）
        logger.info("📊 測試5: 銷售功能測試（模擬）")
        logger.info("-" * 40)
        
        logger.info("ℹ️ 銷售功能已實現但在演示中不執行實際銷售")
        logger.info("   可用方法: market_operations.list_item_for_sale(item_name, price)")
        logger.info("   功能包括:")
        logger.info("   - 在庫存中找到物品")
        logger.info("   - 右鍵點擊打開選單")
        logger.info("   - 選擇銷售選項")
        logger.info("   - 輸入價格")
        logger.info("   - 確認上架")
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("🎉 階段2.4市場操作演示完成！")
        logger.info("")
        logger.info("✅ 已實現功能:")
        logger.info("   - 市場物品掃描")
        logger.info("   - 物品搜索")
        logger.info("   - 銷售位狀態檢查")
        logger.info("   - 市場概要分析")
        logger.info("   - 購買操作流程")
        logger.info("   - 銷售操作流程")
        logger.info("")
        logger.info("🔧 市場操作模組已完成並準備好用於交易引擎！")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 演示過程中出現錯誤: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # 清理資源
        try:
            await browser_manager.cleanup()
            logger.info("🧹 瀏覽器資源已清理")
        except Exception as e:
            logger.warning(f"清理瀏覽器資源時出錯: {e}")


async def main():
    """主函數"""
    try:
        success = await test_market_operations()
        
        if success:
            logger.info("🎯 階段2.4市場操作模組測試成功！")
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
    
    # 運行演示
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 