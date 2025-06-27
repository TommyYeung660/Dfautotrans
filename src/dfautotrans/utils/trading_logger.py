"""
Dead Frontier 自動交易系統 - 詳細交易日誌記錄器

專門記錄交易過程中的所有詳細操作，包括：
- 每個交易週期的完整流程
- 資金變化和庫存變化
- 購買和銷售的詳細記錄
- 時間統計和性能分析
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path

@dataclass
class ResourceSnapshot:
    """資源快照"""
    timestamp: str
    current_cash: float
    bank_balance: float
    total_funds: float
    inventory_used: int
    inventory_total: int
    storage_used: int
    storage_total: int
    selling_slots_used: int
    selling_slots_total: int
    
    @classmethod
    def from_system_resources(cls, resources, timestamp: str = None):
        """從SystemResources創建快照"""
        if timestamp is None:
            timestamp = datetime.now().isoformat()
        
        return cls(
            timestamp=timestamp,
            current_cash=getattr(resources, 'current_cash', 0),
            bank_balance=getattr(resources, 'bank_balance', 0),
            total_funds=getattr(resources, 'total_funds', 0),
            inventory_used=getattr(resources, 'inventory_used', 0),
            inventory_total=getattr(resources, 'inventory_total', 0),
            storage_used=getattr(resources, 'storage_used', 0),
            storage_total=getattr(resources, 'storage_total', 0),
            selling_slots_used=getattr(resources, 'selling_slots_used', 0),
            selling_slots_total=getattr(resources, 'selling_slots_total', 0)
        )

@dataclass
class TransactionRecord:
    """交易記錄"""
    timestamp: str
    transaction_type: str  # 'purchase', 'sale', 'withdrawal', 'deposit'
    item_name: str
    quantity: int
    unit_price: float
    total_price: float
    success: bool
    details: Dict[str, Any]

@dataclass
class CycleRecord:
    """交易週期記錄"""
    cycle_id: str
    start_time: str
    end_time: Optional[str] = None
    duration_seconds: Optional[float] = None
    
    # 階段時間記錄
    login_duration: Optional[float] = None
    resource_check_duration: Optional[float] = None
    space_management_duration: Optional[float] = None
    market_analysis_duration: Optional[float] = None
    buying_duration: Optional[float] = None
    selling_duration: Optional[float] = None
    
    # 資源快照
    resources_before: Optional[ResourceSnapshot] = None
    resources_after: Optional[ResourceSnapshot] = None
    
    # 交易記錄
    transactions: List[TransactionRecord] = None
    
    # 統計數據
    total_purchases: int = 0
    total_sales: int = 0
    total_spent: float = 0.0
    total_earned: float = 0.0
    net_profit: float = 0.0
    
    # 錯誤記錄
    errors: List[str] = None
    success: bool = True
    
    def __post_init__(self):
        if self.transactions is None:
            self.transactions = []
        if self.errors is None:
            self.errors = []

class TradingLogger:
    """交易日誌記錄器"""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # 創建日誌文件
        self.trading_log_file = self.log_dir / "detailed_trading.log"
        self.json_log_file = self.log_dir / "trading_data.jsonl"
        
        # 設置日誌記錄器
        self.logger = logging.getLogger("trading_detail")
        self.logger.setLevel(logging.INFO)
        
        # 創建文件處理器
        if not self.logger.handlers:
            handler = logging.FileHandler(self.trading_log_file, encoding='utf-8')
            formatter = logging.Formatter(
                '%(asctime)s | %(levelname)s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        
        # 當前週期記錄
        self.current_cycle: Optional[CycleRecord] = None
        self.stage_start_time: Optional[datetime] = None
        
        self.logger.info("=" * 80)
        self.logger.info("🚀 交易日誌記錄器已啟動")
        self.logger.info("=" * 80)
    
    def start_cycle(self, cycle_id: str = None) -> str:
        """開始新的交易週期"""
        if cycle_id is None:
            cycle_id = f"cycle_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.current_cycle = CycleRecord(
            cycle_id=cycle_id,
            start_time=datetime.now().isoformat()
        )
        
        self.logger.info(f"🔄 開始交易週期: {cycle_id}")
        self.logger.info(f"⏰ 開始時間: {self.current_cycle.start_time}")
        
        return cycle_id
    
    def end_cycle(self, success: bool = True):
        """結束當前交易週期"""
        if not self.current_cycle:
            return
        
        end_time = datetime.now()
        self.current_cycle.end_time = end_time.isoformat()
        self.current_cycle.success = success
        
        # 計算總時長
        start_time = datetime.fromisoformat(self.current_cycle.start_time)
        self.current_cycle.duration_seconds = (end_time - start_time).total_seconds()
        
        # 計算統計數據
        self._calculate_cycle_statistics()
        
        # 記錄週期總結
        self._log_cycle_summary()
        
        # 保存到JSON文件
        self._save_cycle_to_json()
        
        self.current_cycle = None
    
    def start_stage(self, stage_name: str):
        """開始交易階段"""
        self.stage_start_time = datetime.now()
        self.logger.info(f"📋 開始階段: {stage_name}")
    
    def end_stage(self, stage_name: str, success: bool = True):
        """結束交易階段"""
        if not self.stage_start_time or not self.current_cycle:
            return
        
        duration = (datetime.now() - self.stage_start_time).total_seconds()
        
        # 記錄階段時長
        if stage_name == "login":
            self.current_cycle.login_duration = duration
        elif stage_name == "resource_check":
            self.current_cycle.resource_check_duration = duration
        elif stage_name == "space_management":
            self.current_cycle.space_management_duration = duration
        elif stage_name == "market_analysis":
            self.current_cycle.market_analysis_duration = duration
        elif stage_name == "buying":
            self.current_cycle.buying_duration = duration
        elif stage_name == "selling":
            self.current_cycle.selling_duration = duration
        
        status = "✅ 成功" if success else "❌ 失敗"
        self.logger.info(f"📋 階段完成: {stage_name} - {status} - 耗時: {duration:.1f}秒")
        
        self.stage_start_time = None
    
    def record_resource_snapshot(self, resources, label: str = ""):
        """記錄資源快照"""
        if not self.current_cycle:
            return
        
        snapshot = ResourceSnapshot.from_system_resources(resources)
        
        if label == "before":
            self.current_cycle.resources_before = snapshot
        elif label == "after":
            self.current_cycle.resources_after = snapshot
        
        self.logger.info(f"💰 資源快照 ({label}):")
        self.logger.info(f"   現金: ${snapshot.current_cash:,.2f}")
        self.logger.info(f"   銀行: ${snapshot.bank_balance:,.2f}")
        self.logger.info(f"   總資金: ${snapshot.total_funds:,.2f}")
        self.logger.info(f"   庫存: {snapshot.inventory_used}/{snapshot.inventory_total}")
        self.logger.info(f"   倉庫: {snapshot.storage_used}/{snapshot.storage_total}")
        self.logger.info(f"   銷售位: {snapshot.selling_slots_used}/{snapshot.selling_slots_total}")
    
    def record_withdrawal(self, amount: float, success: bool = True):
        """記錄提款操作"""
        self.logger.info(f"🏦 銀行提款: ${amount:,.2f} - {'✅ 成功' if success else '❌ 失敗'}")
        
        if self.current_cycle:
            transaction = TransactionRecord(
                timestamp=datetime.now().isoformat(),
                transaction_type="withdrawal",
                item_name="Bank Withdrawal",
                quantity=1,
                unit_price=amount,
                total_price=amount,
                success=success,
                details={"operation": "bank_withdrawal"}
            )
            self.current_cycle.transactions.append(transaction)
    
    def record_storage_operation(self, operation: str, item_count: int, success: bool = True):
        """記錄倉庫操作"""
        self.logger.info(f"📦 倉庫操作: {operation} {item_count}個物品 - {'✅ 成功' if success else '❌ 失敗'}")
        
        if self.current_cycle:
            transaction = TransactionRecord(
                timestamp=datetime.now().isoformat(),
                transaction_type="deposit",
                item_name=f"Storage {operation}",
                quantity=item_count,
                unit_price=0.0,
                total_price=0.0,
                success=success,
                details={"operation": operation, "item_count": item_count}
            )
            self.current_cycle.transactions.append(transaction)
    
    def record_purchase(self, item_name: str, quantity: int, unit_price: float, total_price: float, success: bool = True, details: Dict = None):
        """記錄購買操作"""
        if details is None:
            details = {}
        
        self.logger.info(f"🛒 購買: {item_name} x{quantity} @ ${unit_price:.2f} = ${total_price:.2f} - {'✅ 成功' if success else '❌ 失敗'}")
        
        if self.current_cycle:
            transaction = TransactionRecord(
                timestamp=datetime.now().isoformat(),
                transaction_type="purchase",
                item_name=item_name,
                quantity=quantity,
                unit_price=unit_price,
                total_price=total_price,
                success=success,
                details=details
            )
            self.current_cycle.transactions.append(transaction)
            
            if success:
                self.current_cycle.total_purchases += 1
                self.current_cycle.total_spent += total_price
    
    def record_sale(self, item_name: str, quantity: int, unit_price: float, total_price: float, success: bool = True, details: Dict = None):
        """記錄銷售操作"""
        if details is None:
            details = {}
        
        self.logger.info(f"💰 銷售: {item_name} x{quantity} @ ${unit_price:.2f} = ${total_price:.2f} - {'✅ 成功' if success else '❌ 失敗'}")
        
        if self.current_cycle:
            transaction = TransactionRecord(
                timestamp=datetime.now().isoformat(),
                transaction_type="sale",
                item_name=item_name,
                quantity=quantity,
                unit_price=unit_price,
                total_price=total_price,
                success=success,
                details=details
            )
            self.current_cycle.transactions.append(transaction)
            
            if success:
                self.current_cycle.total_sales += 1
                self.current_cycle.total_earned += total_price
    
    def record_market_scan(self, search_term: str, items_found: int, duration: float):
        """記錄市場掃描"""
        self.logger.info(f"🔍 市場掃描: 搜索詞='{search_term}', 找到{items_found}個物品, 耗時{duration:.1f}秒")
    
    def record_error(self, error_message: str, stage: str = ""):
        """記錄錯誤"""
        full_message = f"[{stage}] {error_message}" if stage else error_message
        self.logger.error(f"❌ 錯誤: {full_message}")
        
        if self.current_cycle:
            self.current_cycle.errors.append(full_message)
    
    def record_wait(self, wait_type: str, duration: float, reason: str = ""):
        """記錄等待時間"""
        reason_text = f" - {reason}" if reason else ""
        self.logger.info(f"⏸️ 等待: {wait_type}, 時長: {duration:.1f}秒{reason_text}")
    
    def _calculate_cycle_statistics(self):
        """計算週期統計數據"""
        if not self.current_cycle:
            return
        
        # 計算淨利潤
        self.current_cycle.net_profit = self.current_cycle.total_earned - self.current_cycle.total_spent
        
        # 計算資源變化
        if self.current_cycle.resources_before and self.current_cycle.resources_after:
            before = self.current_cycle.resources_before
            after = self.current_cycle.resources_after
            
            cash_change = after.current_cash - before.current_cash
            funds_change = after.total_funds - before.total_funds
            
            self.logger.info(f"💵 資金變化: 現金 {cash_change:+.2f}, 總資金 {funds_change:+.2f}")
    
    def _log_cycle_summary(self):
        """記錄週期總結"""
        if not self.current_cycle:
            return
        
        cycle = self.current_cycle
        
        self.logger.info("=" * 60)
        self.logger.info(f"📊 交易週期總結: {cycle.cycle_id}")
        self.logger.info("=" * 60)
        self.logger.info(f"⏰ 總時長: {cycle.duration_seconds:.1f}秒 ({cycle.duration_seconds/60:.1f}分鐘)")
        self.logger.info(f"📈 結果: {'✅ 成功' if cycle.success else '❌ 失敗'}")
        
        # 階段時長統計
        self.logger.info("⏱️ 階段時長:")
        if cycle.login_duration:
            self.logger.info(f"   登錄檢查: {cycle.login_duration:.1f}秒")
        if cycle.resource_check_duration:
            self.logger.info(f"   資源檢查: {cycle.resource_check_duration:.1f}秒")
        if cycle.space_management_duration:
            self.logger.info(f"   空間管理: {cycle.space_management_duration:.1f}秒")
        if cycle.market_analysis_duration:
            self.logger.info(f"   市場分析: {cycle.market_analysis_duration:.1f}秒")
        if cycle.buying_duration:
            self.logger.info(f"   購買階段: {cycle.buying_duration:.1f}秒")
        if cycle.selling_duration:
            self.logger.info(f"   銷售階段: {cycle.selling_duration:.1f}秒")
        
        # 交易統計
        self.logger.info("💹 交易統計:")
        self.logger.info(f"   購買次數: {cycle.total_purchases}")
        self.logger.info(f"   銷售次數: {cycle.total_sales}")
        self.logger.info(f"   總支出: ${cycle.total_spent:.2f}")
        self.logger.info(f"   總收入: ${cycle.total_earned:.2f}")
        self.logger.info(f"   淨利潤: ${cycle.net_profit:.2f}")
        
        # 錯誤統計
        if cycle.errors:
            self.logger.info(f"⚠️ 錯誤數量: {len(cycle.errors)}")
            for error in cycle.errors:
                self.logger.info(f"   - {error}")
        
        self.logger.info("=" * 60)
    
    def _save_cycle_to_json(self):
        """保存週期數據到JSON文件"""
        if not self.current_cycle:
            return
        
        try:
            cycle_data = asdict(self.current_cycle)
            
            with open(self.json_log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(cycle_data, ensure_ascii=False) + '\n')
                
        except Exception as e:
            self.logger.error(f"❌ 保存週期數據失敗: {e}")
    
    def get_session_summary(self) -> Dict[str, Any]:
        """獲取會話總結"""
        try:
            cycles = []
            if self.json_log_file.exists():
                with open(self.json_log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            cycles.append(json.loads(line))
            
            if not cycles:
                return {"message": "沒有找到交易週期數據"}
            
            # 計算總統計
            total_cycles = len(cycles)
            successful_cycles = sum(1 for c in cycles if c.get('success', False))
            total_duration = sum(c.get('duration_seconds', 0) for c in cycles)
            total_purchases = sum(c.get('total_purchases', 0) for c in cycles)
            total_sales = sum(c.get('total_sales', 0) for c in cycles)
            total_spent = sum(c.get('total_spent', 0) for c in cycles)
            total_earned = sum(c.get('total_earned', 0) for c in cycles)
            net_profit = sum(c.get('net_profit', 0) for c in cycles)
            
            return {
                "total_cycles": total_cycles,
                "successful_cycles": successful_cycles,
                "success_rate": (successful_cycles / total_cycles * 100) if total_cycles > 0 else 0,
                "total_duration_minutes": total_duration / 60,
                "average_cycle_duration_minutes": (total_duration / total_cycles / 60) if total_cycles > 0 else 0,
                "total_purchases": total_purchases,
                "total_sales": total_sales,
                "total_spent": total_spent,
                "total_earned": total_earned,
                "net_profit": net_profit,
                "profit_per_cycle": (net_profit / total_cycles) if total_cycles > 0 else 0
            }
            
        except Exception as e:
            return {"error": f"獲取會話總結失敗: {e}"} 