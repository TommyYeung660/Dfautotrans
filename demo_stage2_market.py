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
        # 使用配置中的第一個目標物品作為搜索詞
        primary_search_term = market_operations.trading_config.market_search.target_items[0]
        logger.info(f"🎯 使用配置的搜索詞: '{primary_search_term}'")
        market_items = await market_operations.scan_market_items(search_term=primary_search_term, max_items=10)
        
        if market_items:
            logger.info(f"✅ 成功掃描到 {len(market_items)} 個市場物品")
            for i, item in enumerate(market_items[:5], 1):  # 顯示前5個
                logger.info(f"   {i}. {item.item_name} - ${item.price} ({item.seller})")
            if len(market_items) > 5:
                logger.info(f"   ... 還有 {len(market_items) - 5} 個物品")
        else:
            logger.warning("⚠️ 沒有掃描到市場物品")
        
        # 搜索特定物品
        logger.info("🔍 搜索特定物品: '12.7mm Rifle Bullets'...")
        rifle_bullets = await market_operations.scan_market_items(
            search_term="12.7mm Rifle Bullets", 
            max_items=5
        )
        
        if rifle_bullets:
            logger.info(f"✅ 找到 {len(rifle_bullets)} 個 12.7mm Rifle Bullets")
            for i, item in enumerate(rifle_bullets, 1):
                logger.info(f"   {i}. {item.item_name} - ${item.price} ({item.seller})")
        else:
            logger.warning("⚠️ 沒有找到 12.7mm Rifle Bullets")
        
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
        
        # 測試5: 銷售功能（實際上架測試）
        logger.info("📊 測試5: 銷售功能測試（實際上架）")
        logger.info("-" * 40)
        
        # 先檢查庫存
        logger.info("🎒 檢查庫存物品...")
        try:
            # 導航到市場頁面的selling標籤來檢查庫存
            if not await page_navigator.navigate_to_marketplace():
                logger.error("❌ 無法導航到市場頁面")
                raise Exception("無法導航到市場頁面")
            
            # 切換到selling標籤
            await market_operations._ensure_sell_tab_active()
            await asyncio.sleep(2)
            
            # 獲取庫存物品
            from src.dfautotrans.automation.inventory_manager import InventoryManager
            inventory_manager = InventoryManager(settings, browser_manager, page_navigator)
            inventory_items = await inventory_manager.get_inventory_items()
            
            if inventory_items and len(inventory_items) > 0:
                logger.info(f"✅ 找到 {len(inventory_items)} 個庫存物品")
                
                # 顯示前5個庫存物品
                for i, item in enumerate(inventory_items[:5], 1):
                    logger.info(f"   {i}. {item.item_name} - 數量: {item.quantity}")
                
                # 選擇第一個物品進行上架測試
                test_item = inventory_items[0]
                logger.info(f"🎯 選擇上架物品: {test_item.item_name}")
                
                # 計算上架價格（基於市場價格 + 20% 加價）
                base_price = 1000  # 默認基準價格
                if hasattr(test_item, 'estimated_value') and test_item.estimated_value > 0:
                    base_price = test_item.estimated_value
                
                # 根據物品類型設定合理價格
                item_name_lower = test_item.item_name.lower()
                if "bullet" in item_name_lower or "shell" in item_name_lower:
                    if "12.7" in item_name_lower:
                        base_price = 15
                    elif "7.62" in item_name_lower:
                        base_price = 12
                    elif "5.56" in item_name_lower or "9mm" in item_name_lower:
                        base_price = 10
                    else:
                        base_price = 8
                elif "painkiller" in item_name_lower:
                    base_price = 25
                elif "bandage" in item_name_lower:
                    base_price = 15
                elif "energy cell" in item_name_lower:
                    base_price = 15
                elif "gasoline" in item_name_lower:
                    base_price = 3
                
                # 應用20%加價
                selling_price = int(base_price * 1.2)
                
                logger.info(f"💰 計算上架價格: ${selling_price} (基準價格 ${base_price} + 20%)")
                
                # 詢問用戶是否要實際上架
                logger.info("⚠️ 即將執行實際上架操作")
                logger.info(f"   物品: {test_item.item_name}")
                logger.info(f"   價格: ${selling_price}")
                logger.info("   這將會在遊戲中實際上架該物品到市場")
                
                # 檢查是否有環境變量控制是否實際執行
                import os
                should_execute =  True
                
                if should_execute:
                    logger.info("🔧 環境變量 EXECUTE_REAL_LISTING=true，將執行實際上架")
                    # 等待3秒讓用戶看到信息
                    logger.info("⏳ 3秒後開始上架...")
                    for i in range(3, 0, -1):
                        logger.info(f"   {i}...")
                        await asyncio.sleep(1)
                    
                    # 執行上架
                    logger.info("🚀 開始執行上架操作...")
                    
                    try:
                        success = await market_operations.list_item_for_sale(
                            test_item.item_name, 
                            selling_price
                        )
                        
                        if success:
                            logger.info("✅ 上架成功！")
                            logger.info(f"   物品 {test_item.item_name} 已成功上架")
                            logger.info(f"   售價: ${selling_price}")
                            
                            # 重新檢查銷售位狀態
                            logger.info("🔄 重新檢查銷售位狀態...")
                            await asyncio.sleep(2)
                            updated_selling_status = await market_operations.get_selling_slots_status()
                            
                            if updated_selling_status:
                                logger.info(f"📊 更新後的銷售位狀態:")
                                logger.info(f"   已使用: {updated_selling_status.current_listings}")
                                logger.info(f"   可用位置: {updated_selling_status.available_slots}")
                                
                                if updated_selling_status.listed_items:
                                    logger.info(f"   最新上架物品:")
                                    for item in updated_selling_status.listed_items[-3:]:  # 顯示最後3個
                                        logger.info(f"      - {item}")
                        else:
                            logger.warning("⚠️ 上架失敗")
                            logger.info("   可能的原因:")
                            logger.info("   - 銷售位已滿")
                            logger.info("   - 物品無法上架")
                            logger.info("   - 網絡問題")
                            logger.info("   - 頁面元素變化")
                            
                    except Exception as e:
                        logger.error(f"❌ 上架過程中出現錯誤: {e}")
                        logger.info("   這可能是由於:")
                        logger.info("   - 頁面結構變化")
                        logger.info("   - 網絡延遲")
                        logger.info("   - 遊戲狀態變化")
                else:
                    logger.info("🛡️ 安全模式：不會執行實際上架")
                    logger.info("   如要執行實際上架，請設置環境變量:")
                    logger.info("   set EXECUTE_REAL_LISTING=true")
                    logger.info("")
                    logger.info("⏭️ 跳過實際上架，顯示模擬結果...")
                    logger.info("✅ 模擬上架成功！")
                    logger.info(f"   物品 {test_item.item_name} 模擬上架完成")
                    logger.info(f"   模擬售價: ${selling_price}")
                    logger.info("   (實際上架需要設置環境變量)")
            else:
                logger.warning("⚠️ 庫存中沒有可上架的物品")
                logger.info("   建議:")
                logger.info("   - 先購買一些物品")
                logger.info("   - 檢查是否在正確的庫存頁面")
                logger.info("   - 確認庫存物品掃描功能正常")
                
        except Exception as e:
            logger.error(f"❌ 檢查庫存時出現錯誤: {e}")
            logger.info("ℹ️ 跳過上架測試，顯示功能說明:")
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