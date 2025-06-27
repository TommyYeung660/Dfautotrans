#!/usr/bin/env python3
"""
上架功能調試測試
專門測試庫存物品匹配和上架功能
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
from src.dfautotrans.automation.inventory_manager import InventoryManager
from src.dfautotrans.core.page_navigator import PageNavigator
from src.dfautotrans.data.database import DatabaseManager
from src.dfautotrans.config.trading_config import TradingConfigManager


def normalize_item_name(item_name: str) -> str:
    """標準化物品名稱，用於匹配"""
    # 移除多餘空格並轉為小寫
    normalized = item_name.strip().lower()
    
    # 處理常見的名稱變化
    replacements = {
        "12.7mm rifle bullets": "12.7 rifle bullets",
        "14mm rifle bullets": "14 rifle bullets", 
        "9mm rifle bullets": "9 rifle bullets",
        "10 gauge shells": "10 gauge shells",
        "12 gauge shells": "12 gauge shells",
        "energy cell": "energy cell",
        "gasoline": "gasoline"
    }
    
    for config_name, inventory_name in replacements.items():
        if config_name in normalized:
            return inventory_name
    
    return normalized


def find_matching_inventory_item(inventory_items, target_items):
    """在庫存中找到與配置目標物品匹配的物品"""
    matches = []
    
    logger.info(f"🔍 在 {len(inventory_items)} 個庫存物品中尋找匹配項")
    logger.info(f"🎯 目標物品: {target_items}")
    
    for inventory_item in inventory_items:
        inventory_name = normalize_item_name(inventory_item.item_name)
        logger.debug(f"檢查庫存物品: '{inventory_item.item_name}' -> 標準化: '{inventory_name}'")
        
        for target_item in target_items:
            target_name = normalize_item_name(target_item)
            logger.debug(f"  與目標物品比較: '{target_item}' -> 標準化: '{target_name}'")
            
            if target_name == inventory_name:
                matches.append({
                    'inventory_item': inventory_item,
                    'config_item': target_item,
                    'match_type': 'exact'
                })
                logger.info(f"✅ 找到完全匹配: '{inventory_item.item_name}' <-> '{target_item}'")
                break
            elif target_name in inventory_name or inventory_name in target_name:
                matches.append({
                    'inventory_item': inventory_item,
                    'config_item': target_item,
                    'match_type': 'partial'
                })
                logger.info(f"⚠️ 找到部分匹配: '{inventory_item.item_name}' <-> '{target_item}'")
                break
    
    return matches


def calculate_listing_price(item_name: str, quantity: int, base_price_map: dict) -> int:
    """計算上架價格（總價 = 單價 × 數量）
    
    使用合理的單價基準，參考trading_config.json中的max_price_per_unit配置
    """
    normalized_name = normalize_item_name(item_name)
    
    # 基於物品類型的合理單價基準 (參考配置中的max_price_per_unit)
    # 配置中的max_price_per_unit: 12.7mm=11.0, 14mm=13.0, 9mm=11.0, 10gauge=15.0, 12gauge=16.0, energy=15.0, gas=3.0
    # 我們使用略低於max_price的價格作為基準單價，確保加價後不超過max_price
    unit_price_map = {
        "12.7 rifle bullets": 9.0,   # 加價後$10.8，低於配置的11.0
        "14 rifle bullets": 10.5,    # 加價後$12.6，低於配置的13.0  
        "9 rifle bullets": 9.0,      # 加價後$10.8，低於配置的11.0
        "10 gauge shells": 12.0,     # 加價後$14.4，低於配置的15.0
        "12 gauge shells": 13.0,     # 加價後$15.6，低於配置的16.0
        "energy cell": 12.0,         # 加價後$14.4，低於配置的15.0
        "gasoline": 2.5,              # 加價後$3.0，等於配置的3.0（通常數量為1）
        "painkiller": 25.0,           # 醫療用品
        "bandage": 15.0,              # 醫療用品
        "cooked fresh meat": 8.0      # 食物
    }
    
    # 尋找匹配的基準單價
    base_unit_price = None
    for price_item, unit_price in unit_price_map.items():
        if price_item in normalized_name:
            base_unit_price = unit_price
            break
    
    if base_unit_price is None:
        logger.warning(f"⚠️ 未找到 '{item_name}' 的基準單價，使用默認值 $5.0")
        base_unit_price = 5.0
    
    # 計算總價 = 單價 × 數量 × 加價倍數
    markup_multiplier = 1.2  # 20%加價
    total_price = int(base_unit_price * quantity * markup_multiplier)
    
    logger.info(f"💰 '{item_name}' 價格計算:")
    logger.info(f"   數量: {quantity}")
    logger.info(f"   基準單價: ${base_unit_price} (參考配置max_price_per_unit)")
    logger.info(f"   加價倍數: {markup_multiplier}")
    logger.info(f"   總價: ${total_price}")
    
    return total_price


def test_price_calculation():
    """測試價格計算邏輯"""
    logger.info("🧮 測試價格計算邏輯")
    logger.info("=" * 40)
    
    test_cases = [
        ("12.7 Rifle Bullets", 1200),  # 1200發，單價$9 -> 總價$10,800 (加價後$12,960)
        ("14 Rifle Bullets", 800),     # 800發，單價$11 -> 總價$8,800 (加價後$10,560)
        ("9 Rifle Bullets", 1500),     # 1500發，單價$9 -> 總價$13,500 (加價後$16,200)
        ("10 Gauge Shells", 400),      # 400發，單價$13 -> 總價$5,200 (加價後$6,240)
        ("12 Gauge Shells", 300),      # 300發，單價$14 -> 總價$4,200 (加價後$5,040)
        ("Energy Cell", 600),          # 600個，單價$13 -> 總價$7,800 (加價後$9,360)
        ("Gasoline", 1),               # 1個，單價$2.5 -> 總價$2.5 (加價後$3)
        ("Painkiller", 1),             # 1個，單價$25 -> 總價$25 (加價後$30)
        ("Bandage", 5)                 # 5個，單價$15 -> 總價$75 (加價後$90)
    ]
    
    logger.info("📊 預期結果 vs 實際結果對比:")
    logger.info("")
    
    for item_name, quantity in test_cases:
        total_price = calculate_listing_price(item_name, quantity, {})
        unit_price = total_price / quantity
        
        # 計算預期的配置參考價格
        config_prices = {
            "12.7 Rifle Bullets": 11.0,
            "14 Rifle Bullets": 13.0, 
            "9 Rifle Bullets": 11.0,
            "10 Gauge Shells": 15.0,
            "12 Gauge Shells": 16.0,
            "Energy Cell": 15.0,
            "Gasoline": 3.0
        }
        
        config_max_price = config_prices.get(item_name, "N/A")
        
        logger.info(f"📊 {item_name}:")
        logger.info(f"   數量: {quantity}")
        logger.info(f"   配置max_price_per_unit: ${config_max_price}")
        logger.info(f"   實際計算單價: ${unit_price:.2f}")
        logger.info(f"   總價: ${total_price}")
        
        # 檢查單價是否合理（應該低於或接近配置的max_price_per_unit）
        if isinstance(config_max_price, (int, float)):
            if unit_price <= config_max_price:
                logger.info(f"   ✅ 單價合理 (≤ ${config_max_price})")
            else:
                logger.info(f"   ⚠️ 單價偏高 (> ${config_max_price})")
        
        logger.info("")


def test_selling_strategy():
    """測試簡化後的銷售策略"""
    logger.info("🧪 測試簡化後的銷售策略")
    logger.info("=" * 40)
    
    # 導入必要的模組
    from src.dfautotrans.strategies.selling_strategy import SellingStrategy
    from src.dfautotrans.data.models import InventoryItemData, TradingConfiguration
    from src.dfautotrans.config.trading_config import TradingConfigManager
    
    # 載入配置
    config_manager = TradingConfigManager()
    trading_config = config_manager.load_config()
    
    # 創建銷售策略實例
    legacy_config = TradingConfiguration()  # 創建空的向後兼容配置
    selling_strategy = SellingStrategy(legacy_config, trading_config)
    
    # 測試物品列表
    test_items = [
        InventoryItemData(item_name="12.7mm Rifle Bullets", quantity=1200, slot_position=1),
        InventoryItemData(item_name="14mm Rifle Bullets", quantity=800, slot_position=2),
        InventoryItemData(item_name="9mm Rifle Bullets", quantity=1500, slot_position=3),
        InventoryItemData(item_name="10 Gauge Shells", quantity=400, slot_position=4),
        InventoryItemData(item_name="12 Gauge Shells", quantity=300, slot_position=5),
        InventoryItemData(item_name="Energy Cell", quantity=600, slot_position=6),
        InventoryItemData(item_name="Gasoline", quantity=1, slot_position=7),
        InventoryItemData(item_name="Painkiller", quantity=3, slot_position=8),
        InventoryItemData(item_name="Bandage", quantity=5, slot_position=9),
        InventoryItemData(item_name="Unknown Item", quantity=1, slot_position=10),  # 測試不在配置中的物品
    ]
    
    logger.info("📊 測試各物品的定價:")
    logger.info("")
    
    for item in test_items:
        try:
            selling_price = selling_strategy._calculate_selling_price(item)
            total_value = selling_price * item.quantity
            
            # 檢查是否在配置中
            is_in_config = item.item_name in trading_config.market_search.target_items
            
            if is_in_config:
                item_index = trading_config.market_search.target_items.index(item.item_name)
                max_price = trading_config.market_search.max_price_per_unit[item_index]
                status = "✅ 配置物品" if selling_price <= max_price else "⚠️ 超出配置"
            else:
                max_price = "N/A"
                status = "📝 默認定價"
            
            logger.info(f"🔸 {item.item_name}:")
            logger.info(f"   數量: {item.quantity}")
            logger.info(f"   配置max_price: ${max_price}")
            logger.info(f"   計算售價: ${selling_price:.2f}")
            logger.info(f"   總價值: ${total_value:.0f}")
            logger.info(f"   狀態: {status}")
            logger.info("")
            
        except Exception as e:
            logger.error(f"❌ 測試物品 {item.item_name} 時出錯: {e}")
    
    # 測試get_recommended_pricing方法
    logger.info("🔍 測試建議定價方法:")
    test_item_names = ["12.7mm Rifle Bullets", "Painkiller", "Unknown Item"]
    
    for item_name in test_item_names:
        recommended_price = selling_strategy.get_recommended_pricing(item_name)
        logger.info(f"   {item_name}: ${recommended_price:.2f}")
    
    logger.info("")
    logger.info("✅ 銷售策略測試完成！")


async def test_listing_functionality():
    """測試上架功能"""
    
    # 初始化組件
    settings = Settings()
    browser_manager = BrowserManager(settings)
    database_manager = DatabaseManager(settings)
    page_navigator = PageNavigator(browser_manager, settings)
    login_handler = LoginHandler(browser_manager, page_navigator, settings, database_manager)
    market_operations = MarketOperations(settings, browser_manager, page_navigator)
    inventory_manager = InventoryManager(settings, browser_manager, page_navigator)
    
    # 載入交易配置
    config_manager = TradingConfigManager()
    trading_config = config_manager.load_config()
    
    try:
        logger.info("🚀 開始上架功能調試測試")
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
        
        # 步驟1: 載入配置目標物品
        logger.info("📋 步驟1: 載入配置目標物品")
        target_items = trading_config.market_search.target_items
        logger.info(f"🎯 配置中的目標物品 ({len(target_items)} 個):")
        for i, item in enumerate(target_items, 1):
            logger.info(f"   {i}. {item}")
        
        logger.info("")
        
        # 步驟2: 檢查庫存物品
        logger.info("📋 步驟2: 檢查庫存物品")
        
        # 導航到市場頁面的selling標籤
        if not await page_navigator.navigate_to_marketplace():
            logger.error("❌ 無法導航到市場頁面")
            return False
        
        # 切換到selling標籤
        try:
            await market_operations._ensure_sell_tab_active()
            logger.info("✅ 成功切換到selling標籤")
        except Exception as e:
            logger.warning(f"⚠️ 切換selling標籤時出現警告: {e}")
            logger.info("繼續執行...")
        
        await asyncio.sleep(2)
        
        # 獲取庫存物品
        inventory_items = await inventory_manager.get_inventory_items()
        
        if not inventory_items:
            logger.error("❌ 沒有找到庫存物品")
            return False
        
        logger.info(f"✅ 找到 {len(inventory_items)} 個庫存物品:")
        for i, item in enumerate(inventory_items[:10], 1):  # 顯示前10個
            logger.info(f"   {i}. '{item.item_name}' - 數量: {item.quantity}")
        if len(inventory_items) > 10:
            logger.info(f"   ... 還有 {len(inventory_items) - 10} 個物品")
        
        logger.info("")
        
        # 步驟3: 匹配庫存與配置物品
        logger.info("📋 步驟3: 匹配庫存與配置物品")
        matches = find_matching_inventory_item(inventory_items, target_items)
        
        if not matches:
            logger.error("❌ 沒有找到匹配的物品")
            logger.info("💡 建議:")
            logger.info("   1. 檢查配置中的物品名稱是否正確")
            logger.info("   2. 確認庫存中有目標物品")
            logger.info("   3. 檢查名稱標準化邏輯")
            return False
        
        logger.info(f"✅ 找到 {len(matches)} 個匹配項:")
        for i, match in enumerate(matches, 1):
            match_symbol = "🎯" if match['match_type'] == 'exact' else "⚠️"
            logger.info(f"   {i}. {match_symbol} 庫存: '{match['inventory_item'].item_name}' <-> 配置: '{match['config_item']}'")
        
        logger.info("")
        
        # 步驟4: 選擇要上架的物品
        logger.info("📋 步驟4: 選擇要上架的物品")
        
        # 優先選擇完全匹配的物品
        exact_matches = [m for m in matches if m['match_type'] == 'exact']
        selected_match = exact_matches[0] if exact_matches else matches[0]
        
        selected_item = selected_match['inventory_item']
        config_item = selected_match['config_item']
        
        logger.info(f"🎯 選擇上架物品:")
        logger.info(f"   庫存名稱: '{selected_item.item_name}'")
        logger.info(f"   配置名稱: '{config_item}'")
        logger.info(f"   數量: {selected_item.quantity}")
        logger.info(f"   匹配類型: {selected_match['match_type']}")
        
        # 計算上架價格
        selling_price = calculate_listing_price(selected_item.item_name, selected_item.quantity, {})
        
        logger.info("")
        
        # 步驟5: 執行上架
        logger.info("📋 步驟5: 執行上架")
        logger.info("⚠️ 即將執行實際上架操作")
        logger.info(f"   物品: '{selected_item.item_name}'")
        logger.info(f"   價格: ${selling_price}")
        logger.info("   這將會在遊戲中實際上架該物品到市場")
        
        # 等待確認
        logger.info("⏳ 3秒後開始上架...")
        for i in range(3, 0, -1):
            logger.info(f"   {i}...")
            await asyncio.sleep(1)
        
        # 執行上架
        logger.info("🚀 開始執行上架操作...")
        
        try:
            success = await market_operations.list_item_for_sale(
                selected_item.item_name,  # 使用庫存中的實際名稱
                selling_price
            )
            
            if success:
                logger.info("✅ 上架成功！")
                logger.info(f"   物品 '{selected_item.item_name}' 已成功上架")
                logger.info(f"   售價: ${selling_price}")
                
                # 重新檢查銷售位狀態
                logger.info("🔄 重新檢查銷售位狀態...")
                await asyncio.sleep(3)
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
                    logger.warning("⚠️ 無法獲取更新後的銷售位狀態")
                    
            else:
                logger.warning("⚠️ 上架失敗")
                logger.info("   可能的原因:")
                logger.info("   - 銷售位已滿")
                logger.info("   - 物品無法上架")
                logger.info("   - 網絡問題")
                logger.info("   - 頁面元素變化")
                logger.info("   - 物品名稱仍然不匹配")
                
        except Exception as e:
            logger.error(f"❌ 上架過程中出現錯誤: {e}")
            import traceback
            traceback.print_exc()
            logger.info("   這可能是由於:")
            logger.info("   - 頁面結構變化")
            logger.info("   - 網絡延遲")
            logger.info("   - 遊戲狀態變化")
            logger.info("   - 物品選擇器問題")
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("🎉 上架功能調試測試完成！")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 測試過程中出現錯誤: {e}")
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
        # 首先測試價格計算邏輯
        test_price_calculation()
        
        # 測試簡化後的銷售策略
        test_selling_strategy()
        
        success = await test_listing_functionality()
        
        if success:
            logger.info("🎯 上架功能調試測試成功！")
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
    
    # 運行調試測試
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 