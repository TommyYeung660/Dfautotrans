#!/usr/bin/env python3
"""
Dead Frontier 自動交易系統 - 配置演示腳本
演示如何使用新的簡化配置系統
"""

import sys
from pathlib import Path

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from dfautotrans.config.trading_config import TradingConfigManager

def main():
    """演示配置系統功能"""
    print("🎯 Dead Frontier 自動交易系統 - 配置演示")
    print("=" * 60)
    
    # 創建配置管理器
    config_manager = TradingConfigManager("trading_config.json")
    
    try:
        # 載入配置
        print("\n📂 載入配置...")
        config = config_manager.load_config()
        
        # 顯示配置摘要
        config_manager.print_config_summary()
        
        # 演示配置查詢功能
        print("\n🔍 配置查詢演示:")
        print("-" * 30)
        
        # 檢查目標物品
        target_items = config.market_search.target_items
        for item in target_items:
            max_price = config_manager.get_item_max_price(item)
            priority = config_manager.get_item_priority(item)
            is_target = config_manager.is_target_item(item)
            print(f"  {item}:")
            print(f"    最高價格: ${max_price}")
            print(f"    優先級: {priority}")
            print(f"    是目標物品: {is_target}")
        
        # 演示動態配置更新
        print("\n⚙️ 動態配置更新演示:")
        print("-" * 30)
        
        print("更新前的配置:")
        print(f"  12.7mm Rifle Bullets 最高價格: ${config_manager.get_item_max_price('12.7mm Rifle Bullets')}")
        print(f"  最小利潤率: {config.buying.min_profit_margin:.1%}")
        
        # 更新配置
        updates = {
            "market_search.max_price_per_unit": [15.0, 18.0, 30.0, 10.0],  # 提高所有物品價格
            "buying.min_profit_margin": 0.20,  # 提高利潤率要求到20%
            "buying.max_purchases_per_cycle": 10,  # 增加每週期購買數量
            "selling.markup_percentage": 0.30  # 提高加價比例到30%
        }
        
        success = config_manager.update_config(updates)
        if success:
            print("\n✅ 配置更新成功！")
            print("更新後的配置:")
            print(f"  12.7mm Rifle Bullets 最高價格: ${config_manager.get_item_max_price('12.7mm Rifle Bullets')}")
            print(f"  最小利潤率: {config_manager.config.buying.min_profit_margin:.1%}")
            print(f"  每週期最大購買: {config_manager.config.buying.max_purchases_per_cycle}")
            print(f"  標準加價比例: {config_manager.config.selling.markup_percentage:.1%}")
        else:
            print("❌ 配置更新失敗")
        
        # 演示配置驗證
        print("\n🔍 配置驗證演示:")
        print("-" * 30)
        
        try:
            config_manager.validate_config()
            print("✅ 配置驗證通過")
        except Exception as e:
            print(f"❌ 配置驗證失敗: {e}")
        
        # 保存配置
        print("\n💾 保存配置...")
        if config_manager.save_config():
            print("✅ 配置已保存到 trading_config.json")
        else:
            print("❌ 配置保存失敗")
        
        # 演示錯誤處理
        print("\n⚠️ 錯誤處理演示:")
        print("-" * 30)
        
        # 嘗試設置無效配置
        invalid_updates = {
            "market_search.target_items": ["12.7mm Rifle Bullets", "9mm Rifle Bullets"],
            "market_search.max_price_per_unit": [15.0]  # 故意不匹配長度
        }
        
        print("嘗試設置無效配置（數組長度不匹配）...")
        success = config_manager.update_config(invalid_updates)
        if not success:
            print("✅ 正確攔截了無效配置")
        else:
            print("❌ 未能攔截無效配置")
        
        print("\n🎉 配置演示完成！")
        print("\n📋 配置系統特點:")
        print("  ✅ 精確匹配目標物品，避免誤買")
        print("  ✅ 每種物品可設定不同最高價格")
        print("  ✅ 簡化配置結構，易於理解")
        print("  ✅ 自動配置驗證，防止錯誤")
        print("  ✅ 動態配置更新，即時生效")
        print("  ✅ 完整錯誤處理，系統穩定")
        
    except Exception as e:
        print(f"❌ 演示過程中發生錯誤: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 