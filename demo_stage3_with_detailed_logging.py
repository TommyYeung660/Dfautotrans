"""
Dead Frontier 自動交易系統 - Stage 3 實現測試（含詳細日誌記錄）

使用完整的交易引擎進行實際交易，並展示詳細的日誌記錄功能。
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path

from src.dfautotrans.core.trading_engine import TradingEngine
from src.dfautotrans.data.models import TradingConfiguration
from src.dfautotrans.data.database import DatabaseManager
from src.dfautotrans.config.settings import Settings

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler('logs/stage3_detailed.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

async def main():
    """主函數"""
    try:
        logger.info("=" * 80)
        logger.info("🚀 開始 Stage 3 實現測試（含詳細日誌記錄）")
        logger.info("=" * 80)
        
        # 確保日誌目錄存在
        Path("logs").mkdir(exist_ok=True)
        
        # 創建配置
        config = TradingConfiguration(
            max_purchase_amount=50000,
            min_profit_margin=0.20,
            max_items_per_cycle=5,
            enable_auto_selling=True,
            selling_price_multiplier=1.5,
            enable_bank_operations=True,
            min_cash_threshold=10000,
            max_inventory_usage=0.8,
            max_storage_usage=0.9,
            trading_enabled=True
        )
        
        # 創建數據庫管理器
        database_manager = DatabaseManager("dfautotrans.db")
        
        # 創建設置
        settings = Settings()
        
        # 創建交易引擎
        trading_engine = TradingEngine(
            config=config,
            database_manager=database_manager,
            settings=settings,
            trading_config_file="trading_config.json"
        )
        
        logger.info("✅ 交易引擎初始化完成")
        
        # 啟動交易會話
        logger.info("🚀 啟動交易會話...")
        session_started = await trading_engine.start_trading_session()
        
        if not session_started:
            logger.error("❌ 交易會話啟動失敗")
            return
        
        logger.info("✅ 交易會話啟動成功")
        
        # 執行一個交易週期
        logger.info("🔄 執行交易週期...")
        cycle_success = await trading_engine.run_trading_cycle()
        
        if cycle_success:
            logger.info("✅ 交易週期執行成功")
        else:
            logger.warning("⚠️ 交易週期執行失敗")
        
        # 獲取詳細的會話總結
        logger.info("📊 獲取詳細會話總結...")
        session_summary = trading_engine.trading_logger.get_session_summary()
        
        logger.info("=" * 60)
        logger.info("📈 詳細會話總結報告")
        logger.info("=" * 60)
        
        if "error" in session_summary:
            logger.warning(f"⚠️ {session_summary['error']}")
        elif "message" in session_summary:
            logger.info(f"ℹ️ {session_summary['message']}")
        else:
            logger.info(f"📊 總週期數: {session_summary['total_cycles']}")
            logger.info(f"✅ 成功週期: {session_summary['successful_cycles']}")
            logger.info(f"📈 成功率: {session_summary['success_rate']:.1f}%")
            logger.info(f"⏰ 總運行時間: {session_summary['total_duration_minutes']:.1f} 分鐘")
            logger.info(f"⏱️ 平均週期時間: {session_summary['average_cycle_duration_minutes']:.1f} 分鐘")
            logger.info(f"🛒 總購買次數: {session_summary['total_purchases']}")
            logger.info(f"💰 總銷售次數: {session_summary['total_sales']}")
            logger.info(f"💸 總支出: ${session_summary['total_spent']:.2f}")
            logger.info(f"💵 總收入: ${session_summary['total_earned']:.2f}")
            logger.info(f"📊 淨利潤: ${session_summary['net_profit']:.2f}")
            logger.info(f"💹 每週期平均利潤: ${session_summary['profit_per_cycle']:.2f}")
        
        # 停止交易會話
        logger.info("🛑 停止交易會話...")
        await trading_engine.stop_trading_session()
        logger.info("✅ 交易會話已停止")
        
        # 展示生成的日誌文件
        logger.info("=" * 60)
        logger.info("📁 生成的詳細日誌文件")
        logger.info("=" * 60)
        
        logs_dir = Path("logs")
        detailed_log = logs_dir / "detailed_trading.log"
        json_log = logs_dir / "trading_data.jsonl"
        
        if detailed_log.exists():
            size_kb = detailed_log.stat().st_size / 1024
            logger.info(f"📄 詳細日誌文件: {detailed_log} ({size_kb:.1f} KB)")
            
            # 顯示最後幾行日誌
            try:
                with open(detailed_log, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    if len(lines) > 10:
                        logger.info("📝 詳細日誌最後10行:")
                        for line in lines[-10:]:
                            logger.info(f"   {line.strip()}")
            except Exception as e:
                logger.warning(f"⚠️ 讀取詳細日誌文件時出錯: {e}")
        
        if json_log.exists():
            size_kb = json_log.stat().st_size / 1024
            logger.info(f"📊 JSON數據文件: {json_log} ({size_kb:.1f} KB)")
            
            # 顯示JSON文件內容摘要
            try:
                with open(json_log, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    logger.info(f"📋 JSON文件包含 {len(lines)} 條交易週期記錄")
                    
                    if lines:
                        import json
                        latest_record = json.loads(lines[-1])
                        logger.info("📝 最新週期記錄摘要:")
                        logger.info(f"   週期ID: {latest_record.get('cycle_id', 'N/A')}")
                        logger.info(f"   開始時間: {latest_record.get('start_time', 'N/A')}")
                        logger.info(f"   持續時間: {latest_record.get('duration_seconds', 0):.1f} 秒")
                        logger.info(f"   成功狀態: {latest_record.get('success', False)}")
                        logger.info(f"   交易記錄數: {len(latest_record.get('transactions', []))}")
                        logger.info(f"   購買次數: {latest_record.get('total_purchases', 0)}")
                        logger.info(f"   銷售次數: {latest_record.get('total_sales', 0)}")
                        logger.info(f"   淨利潤: ${latest_record.get('net_profit', 0):.2f}")
                        
                        # 顯示階段時間分析
                        stages = {
                            'login_duration': '登錄檢查',
                            'resource_check_duration': '資源檢查',
                            'space_management_duration': '空間管理',
                            'market_analysis_duration': '市場分析',
                            'buying_duration': '購買階段',
                            'selling_duration': '銷售階段'
                        }
                        
                        logger.info("📊 階段時間分析:")
                        for key, name in stages.items():
                            duration = latest_record.get(key)
                            if duration is not None:
                                logger.info(f"   {name}: {duration:.1f} 秒")
                        
            except Exception as e:
                logger.warning(f"⚠️ 讀取JSON數據文件時出錯: {e}")
        
        logger.info("=" * 80)
        logger.info("🎉 Stage 3 實現測試（含詳細日誌記錄）完成")
        logger.info("=" * 80)
        
        logger.info("📚 詳細日誌記錄功能說明:")
        logger.info("1. 📄 detailed_trading.log - 人類可讀的完整操作記錄")
        logger.info("   - 包含每個階段的開始和結束時間")
        logger.info("   - 記錄所有交易操作（購買、銷售、提款、存儲）")
        logger.info("   - 顯示週期總結和統計數據")
        logger.info("")
        logger.info("2. 📊 trading_data.jsonl - 結構化數據，適合程序分析")
        logger.info("   - 每行一個完整的交易週期JSON記錄")
        logger.info("   - 包含所有時間戳、金額、數量等詳細數據")
        logger.info("   - 可用於後續的數據分析和報告生成")
        logger.info("")
        logger.info("3. 🔍 關鍵記錄內容:")
        logger.info("   - 每個階段的執行時間（登錄、資源檢查、市場分析等）")
        logger.info("   - 資源變化快照（現金、銀行餘額、庫存狀態）")
        logger.info("   - 詳細交易記錄（物品名稱、數量、價格、成功狀態）")
        logger.info("   - 等待時間和錯誤記錄")
        logger.info("   - 週期間的統計和利潤分析")
        
    except Exception as e:
        logger.error(f"❌ 測試過程中出錯: {e}")
        import traceback
        logger.error(f"詳細錯誤: {traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(main()) 