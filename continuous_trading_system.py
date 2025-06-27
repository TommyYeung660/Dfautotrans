"""
Dead Frontier 自動交易系統 - 持續運行版本

真正的生產環境交易系統，支持持續不間斷的交易週期。
"""

import asyncio
import logging
import signal
import sys
from datetime import datetime, timedelta
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
        logging.FileHandler('logs/continuous_trading.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class ContinuousTradingSystem:
    """持續運行的交易系統"""
    
    def __init__(self):
        self.running = False
        self.trading_engine = None
        self.total_cycles = 0
        self.successful_cycles = 0
        self.start_time = None
        
    async def initialize(self):
        """初始化交易系統"""
        logger.info("=" * 80)
        logger.info("🚀 Dead Frontier 持續交易系統啟動")
        logger.info("=" * 80)
        
        # 確保日誌目錄存在
        Path("logs").mkdir(exist_ok=True)
        
        # 創建交易配置
        config = TradingConfiguration(
            min_profit_margin=0.20,  # 20% 最小利潤率
            max_item_price=50000.0,  # 最大單件物品價格
            max_total_investment=100000.0,  # 最大總投資額
            max_high_risk_purchases=3,  # 最多高風險購買數量
            diversification_limit=5,  # 同類物品最大購買數量
            normal_wait_seconds=60,  # 正常等待時間
            blocked_wait_seconds=300,  # 阻塞等待時間
            login_retry_wait_seconds=30,  # 登錄重試等待時間
            max_retries=3,  # 最大重試次數
            max_login_retries=5  # 最大登錄重試次數
        )
        
        # 創建設置
        settings = Settings()
        
        # 創建數據庫管理器
        database_manager = DatabaseManager(settings)
        
        # 創建交易引擎
        self.trading_engine = TradingEngine(
            config=config,
            database_manager=database_manager,
            settings=settings,
            trading_config_file="trading_config.json"
        )
        
        logger.info("✅ 交易引擎初始化完成")
        
        # 啟動交易會話
        logger.info("🚀 啟動交易會話...")
        session_started = await self.trading_engine.start_trading_session()
        
        if not session_started:
            logger.error("❌ 交易會話啟動失敗")
            return False
        
        logger.info("✅ 交易會話啟動成功")
        return True
    
    async def run_continuous_trading(self):
        """持續運行交易系統"""
        self.running = True
        self.start_time = datetime.now()
        
        logger.info("🔄 開始持續交易循環...")
        logger.info("📋 使用 Ctrl+C 安全停止系統")
        
        while self.running:
            try:
                cycle_start = datetime.now()
                self.total_cycles += 1
                
                logger.info(f"🔄 執行第 {self.total_cycles} 個交易週期...")
                
                # 執行交易週期
                cycle_success = await self.trading_engine.run_trading_cycle()
                
                if cycle_success:
                    self.successful_cycles += 1
                    logger.info(f"✅ 第 {self.total_cycles} 個週期執行成功")
                else:
                    logger.warning(f"⚠️ 第 {self.total_cycles} 個週期執行失敗")
                
                # 計算週期時間
                cycle_duration = (datetime.now() - cycle_start).total_seconds()
                logger.info(f"⏱️ 週期 {self.total_cycles} 耗時: {cycle_duration:.1f} 秒")
                
                # 顯示累計統計
                success_rate = (self.successful_cycles / self.total_cycles * 100) if self.total_cycles > 0 else 0
                total_runtime = (datetime.now() - self.start_time).total_seconds() / 60
                
                logger.info(f"📊 累計統計: {self.successful_cycles}/{self.total_cycles} 成功 ({success_rate:.1f}%), 運行時間: {total_runtime:.1f} 分鐘")
                
                # 等待下一個週期
                if self.running:
                    wait_time = 60  # 1分鐘等待時間
                    logger.info(f"⏳ 等待 {wait_time} 秒後執行下一個週期...")
                    
                    # 分段等待，便於響應停止信號
                    for i in range(wait_time):
                        if not self.running:
                            break
                        await asyncio.sleep(1)
                        
                        # 每30秒顯示一次剩餘時間
                        if (wait_time - i) % 30 == 0 and (wait_time - i) > 0:
                            logger.info(f"⏳ 還有 {wait_time - i} 秒開始下一週期...")
                
            except Exception as e:
                logger.error(f"❌ 交易週期執行出錯: {e}")
                import traceback
                logger.error(f"詳細錯誤: {traceback.format_exc()}")
                
                # 出錯後等待更長時間再重試
                if self.running:
                    error_wait = 600  # 10分鐘
                    logger.info(f"⚠️ 錯誤後等待 {error_wait} 秒再重試...")
                    await asyncio.sleep(error_wait)
    
    async def shutdown(self):
        """安全關閉系統"""
        logger.info("🛑 正在安全關閉交易系統...")
        self.running = False
        
        if self.trading_engine:
            try:
                await self.trading_engine.stop_trading_session()
                logger.info("✅ 交易會話已停止")
            except Exception as e:
                logger.error(f"❌ 停止交易會話時出錯: {e}")
        
        # 顯示最終統計
        if self.start_time:
            total_runtime = (datetime.now() - self.start_time).total_seconds() / 60
            success_rate = (self.successful_cycles / self.total_cycles * 100) if self.total_cycles > 0 else 0
            
            logger.info("=" * 60)
            logger.info("📈 最終運行統計")
            logger.info("=" * 60)
            logger.info(f"🔄 總週期數: {self.total_cycles}")
            logger.info(f"✅ 成功週期: {self.successful_cycles}")
            logger.info(f"📊 成功率: {success_rate:.1f}%")
            logger.info(f"⏰ 總運行時間: {total_runtime:.1f} 分鐘")
            logger.info(f"⏱️ 平均週期間隔: {total_runtime/self.total_cycles:.1f} 分鐘" if self.total_cycles > 0 else "⏱️ 平均週期間隔: N/A")
        
        logger.info("🎉 交易系統已安全關閉")

# 全局變量用於信號處理
trading_system = None

def signal_handler(signum, frame):
    """處理停止信號"""
    logger.info(f"📢 收到信號 {signum}，準備安全關閉...")
    if trading_system:
        asyncio.create_task(trading_system.shutdown())

async def main():
    """主函數"""
    global trading_system
    
    try:
        # 註冊信號處理器
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # 創建交易系統
        trading_system = ContinuousTradingSystem()
        
        # 初始化系統
        if not await trading_system.initialize():
            logger.error("❌ 系統初始化失敗")
            return
        
        # 開始持續交易
        await trading_system.run_continuous_trading()
        
    except KeyboardInterrupt:
        logger.info("📢 收到鍵盤中斷信號")
    except Exception as e:
        logger.error(f"❌ 系統運行出錯: {e}")
        import traceback
        logger.error(f"詳細錯誤: {traceback.format_exc()}")
    finally:
        if trading_system:
            await trading_system.shutdown()

if __name__ == "__main__":
    asyncio.run(main()) 