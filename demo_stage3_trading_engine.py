#!/usr/bin/env python3
"""
Dead Frontier 自動交易系統 - 階段3交易引擎演示

這個演示展示完整的交易引擎功能，包括：
1. 交易引擎初始化
2. 完整交易週期執行
3. 購買和銷售策略
4. 狀態管理和錯誤處理
5. 性能統計和監控
"""

import sys
import asyncio
import logging
from pathlib import Path
from datetime import datetime

# 添加項目根目錄到Python路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from dfautotrans.core.trading_engine import TradingEngine
from dfautotrans.data.models import TradingConfiguration
from dfautotrans.data.database import DatabaseManager
from dfautotrans.utils.logger import setup_logging
from loguru import logger

# 設置日誌
setup_logging()


async def demo_trading_engine():
    """演示交易引擎的完整功能"""
    
    print("🚀 Dead Frontier 自動交易系統 - 階段3交易引擎演示")
    print("=" * 60)
    
    # 初始化設置和數據庫
    from dfautotrans.config.settings import Settings
    settings = Settings()
    database_manager = DatabaseManager(settings)
    await database_manager.initialize()
    
    # 創建交易配置
    config = TradingConfiguration(
        min_profit_margin=0.15,        # 最小利潤率15%
        max_item_price=50000.0,        # 最大單件物品價格$50,000
        max_total_investment=100000.0, # 最大總投資額$100,000
        max_high_risk_purchases=3,     # 最多3個高風險購買
        diversification_limit=5,       # 同類物品最多5個
        normal_wait_seconds=60,        # 正常等待60秒
        blocked_wait_seconds=300,      # 阻塞等待300秒
        login_retry_wait_seconds=30,   # 登錄重試等待30秒
        max_retries=3,                 # 最大重試次數
        max_login_retries=5            # 最大登錄重試次數
    )
    
    print(f"📋 交易配置:")
    print(f"   最小利潤率: {config.min_profit_margin:.1%}")
    print(f"   最大物品價格: ${config.max_item_price:,.0f}")
    print(f"   最大總投資額: ${config.max_total_investment:,.0f}")
    print(f"   風險管理: 最多{config.max_high_risk_purchases}個高風險購買")
    print(f"   多樣化限制: 同類物品最多{config.diversification_limit}個")
    print()
    
    # 初始化交易引擎
    print("🔧 初始化交易引擎...")
    trading_engine = TradingEngine(config, database_manager)
    
    try:
        # 啟動交易會話
        print("🚀 啟動交易會話...")
        session_started = await trading_engine.start_trading_session()
        
        if not session_started:
            print("❌ 交易會話啟動失敗")
            return
        
        print("✅ 交易會話啟動成功")
        print()
        
        # 執行多個交易週期演示
        max_cycles = 3  # 演示3個交易週期
        successful_cycles = 0
        
        for cycle_num in range(1, max_cycles + 1):
            print(f"🔄 執行交易週期 {cycle_num}/{max_cycles}")
            print("-" * 40)
            
            # 執行交易週期
            cycle_success = await trading_engine.run_trading_cycle()
            
            if cycle_success:
                successful_cycles += 1
                print(f"✅ 交易週期 {cycle_num} 完成")
                
                # 顯示當前狀態
                status = trading_engine.get_current_status()
                print(f"📊 當前狀態: {status['current_state']}")
                print(f"📈 成功週期: {status['session_stats']['successful_cycles']}")
                print(f"🛒 總購買次數: {status['session_stats']['total_purchases']}")
                print(f"💰 總銷售次數: {status['session_stats']['total_sales']}")
                
                # 演示模式：短暫等待而不是完整等待週期
                if cycle_num < max_cycles:
                    print("⏸️ 等待下一個週期...")
                    await asyncio.sleep(5)  # 演示模式：只等待5秒
                
            else:
                print(f"❌ 交易週期 {cycle_num} 失敗")
                # 演示模式：即使失敗也繼續下一個週期
                await asyncio.sleep(3)
            
            print()
        
        # 顯示最終統計
        print("📊 交易會話總結")
        print("=" * 40)
        
        final_status = trading_engine.get_current_status()
        session_stats = final_status['session_stats']
        
        print(f"✅ 成功週期: {session_stats['successful_cycles']}")
        print(f"❌ 失敗週期: {session_stats['failed_cycles']}")
        print(f"🛒 總購買次數: {session_stats['total_purchases']}")
        print(f"💰 總銷售次數: {session_stats['total_sales']}")
        print(f"📈 總利潤: ${session_stats['total_profit']:.2f}")
        
        success_rate = (session_stats['successful_cycles'] / max_cycles * 100) if max_cycles > 0 else 0
        print(f"📊 成功率: {success_rate:.1f}%")
        
        # 測試策略統計
        print()
        print("📈 策略性能分析")
        print("-" * 30)
        
        # 購買策略統計
        buying_stats = trading_engine.buying_strategy.get_strategy_statistics()
        if buying_stats['total_purchases'] > 0:
            print(f"🛒 購買策略統計:")
            print(f"   總購買次數: {buying_stats['total_purchases']}")
            print(f"   平均利潤率: {buying_stats.get('recent_avg_profit_margin', 0):.1%}")
            print(f"   風險分布: {buying_stats.get('risk_distribution', {})}")
            print(f"   熱門物品購買: {buying_stats.get('popular_items_purchased', 0)}")
        
        # 銷售策略統計
        selling_stats = trading_engine.selling_strategy.analyze_selling_performance()
        if selling_stats['total_sales'] > 0:
            print(f"💰 銷售策略統計:")
            print(f"   總銷售次數: {selling_stats['total_sales']}")
            print(f"   總銷售價值: ${selling_stats.get('recent_total_value', 0):,.2f}")
            print(f"   平均銷售價值: ${selling_stats.get('recent_average_value', 0):,.2f}")
            print(f"   熱門物品銷售: {selling_stats.get('popular_items_sold', 0)}")
        
        print()
        print("🎯 階段3交易引擎演示完成!")
        
        if successful_cycles == max_cycles:
            print("✅ 所有交易週期均成功執行")
        elif successful_cycles > 0:
            print(f"⚠️ {successful_cycles}/{max_cycles} 個交易週期成功執行")
        else:
            print("❌ 所有交易週期均失敗")
            
    except KeyboardInterrupt:
        print("\n🛑 用戶中斷演示")
        
    except Exception as e:
        print(f"\n❌ 演示過程中發生錯誤: {e}")
        logger.exception("演示執行錯誤")
        
    finally:
        # 停止交易會話
        print("\n🛑 停止交易會話...")
        await trading_engine.stop_trading_session()
        
        # 關閉數據庫連接
        await database_manager.close()
        
        print("✅ 演示清理完成")


async def demo_strategy_testing():
    """演示策略模組的獨立測試"""
    
    print("\n🧪 策略模組獨立測試")
    print("=" * 40)
    
    # 創建測試配置
    config = TradingConfiguration()
    
    # 測試購買策略
    from dfautotrans.strategies.buying_strategy import BuyingStrategy
    from dfautotrans.data.models import MarketItemData, SystemResources
    
    buying_strategy = BuyingStrategy(config)
    
    # 創建模擬市場物品
    test_items = [
        MarketItemData(
            item_name="12.7mm Rifle Bullets",
            seller="TestSeller1",
            price=12.0,
            quantity=1000,
            location="Outpost"
        ),
        MarketItemData(
            item_name="Pain Killers",
            seller="TestSeller2", 
            price=20.0,
            quantity=50,
            location="Outpost"
        ),
        MarketItemData(
            item_name="Unknown Item",
            seller="TestSeller3",
            price=100.0,
            quantity=10,
            location="Outpost"
        )
    ]
    
    # 創建模擬系統資源
    test_resources = SystemResources(
        current_cash=50000,
        bank_balance=100000,
        total_funds=150000,
        inventory_used=10,
        inventory_total=50,
        storage_used=100,
        storage_total=1000,
        selling_slots_used=5,
        selling_slots_total=30
    )
    
    print("🔍 測試購買策略評估...")
    opportunities = await buying_strategy.evaluate_market_items(test_items, test_resources)
    
    print(f"📊 評估結果: 找到 {len(opportunities)} 個購買機會")
    for i, opp in enumerate(opportunities, 1):
        print(f"   {i}. {opp.item.item_name} - 利潤率: {opp.profit_potential:.1%} - "
              f"風險: {opp.risk_level} - 評分: {opp.priority_score:.1f}")
    
    # 測試銷售策略
    from dfautotrans.strategies.selling_strategy import SellingStrategy
    from dfautotrans.data.models import InventoryItemData, SellingSlotsStatus
    
    selling_strategy = SellingStrategy(config)
    
    # 創建模擬庫存物品
    test_inventory = [
        InventoryItemData(
            item_name="12.7mm Rifle Bullets",
            quantity=500,
            location="inventory"
        ),
        InventoryItemData(
            item_name="Bandages",
            quantity=20,
            location="inventory"
        )
    ]
    
    # 創建模擬銷售位狀態
    test_selling_slots = SellingSlotsStatus(
        current_listings=5,
        max_slots=30,
        listed_items=[]
    )
    
    print("\n💰 測試銷售策略規劃...")
    sell_orders = await selling_strategy.plan_selling_strategy(
        test_inventory, test_selling_slots, test_resources
    )
    
    print(f"📊 銷售規劃結果: 計劃銷售 {len(sell_orders)} 個物品")
    for i, order in enumerate(sell_orders, 1):
        print(f"   {i}. {order.item.item_name} - 價格: ${order.selling_price:.2f} - "
              f"評分: {order.priority_score:.1f}")
    
    print("✅ 策略模組測試完成")


if __name__ == "__main__":
    print("🎮 Dead Frontier 自動交易系統 - 階段3完整演示")
    print("=" * 60)
    print(f"⏰ 演示開始時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        # 運行主要交易引擎演示
        asyncio.run(demo_trading_engine())
        
        # 運行策略測試演示
        asyncio.run(demo_strategy_testing())
        
    except Exception as e:
        print(f"\n❌ 演示執行失敗: {e}")
        logger.exception("演示主程序錯誤")
    
    print(f"\n⏰ 演示結束時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("🎯 階段3交易引擎演示完成!")
    print("\n" + "=" * 60)
    print("📋 階段3開發總結:")
    print("✅ 核心交易引擎 - 完成")
    print("✅ 購買策略模組 - 完成") 
    print("✅ 銷售策略模組 - 完成")
    print("✅ 數據模型擴展 - 完成")
    print("✅ 完整交易週期 - 完成")
    print("✅ 錯誤處理機制 - 完成")
    print("✅ 性能統計監控 - 完成")
    print("\n🚀 準備進入階段4：整合優化!") 