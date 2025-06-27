"""
Dead Frontier 自動交易系統 - 核心交易引擎

這是系統的核心模組，負責協調所有子系統並執行完整的交易週期。
"""

import asyncio
import logging
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from dataclasses import dataclass

from ..data.models import (
    TradingState, TradingCycle, TradingConfiguration,
    SystemResources, MarketCondition, PurchaseOpportunity, SellOrder
)
from ..config.trading_config import TradingConfig, TradingConfigManager

@dataclass
class TradingSessionData:
    """交易會話數據 - 內存版本"""
    session_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    current_state: TradingState = TradingState.IDLE
    current_cycle: Optional[TradingCycle] = None
    
    # 統計數據
    total_purchases: int = 0
    total_sales: int = 0
    total_profit: float = 0.0
    successful_transactions: int = 0
    failed_transactions: int = 0
    
    # 錯誤統計
    login_failures: int = 0
    network_errors: int = 0
    business_errors: int = 0
    
    def __post_init__(self):
        """初始化會話ID"""
        if not self.session_id:
            self.session_id = f"session_{self.start_time.strftime('%Y%m%d_%H%M%S')}"
from ..automation.browser_manager import BrowserManager
from ..automation.login_handler import LoginHandler
from ..automation.market_operations import MarketOperations
from ..automation.inventory_manager import InventoryManager
from ..automation.bank_operations import BankOperations
from ..strategies.buying_strategy import BuyingStrategy
from ..strategies.selling_strategy import SellingStrategy
from ..core.state_machine import StateMachine
from ..core.page_navigator import PageNavigator
from ..data.database import DatabaseManager
from ..utils.trading_logger import TradingLogger

logger = logging.getLogger(__name__)


class TradingEngine:
    """Dead Frontier 自動交易引擎核心類"""
    
    def __init__(self, config: TradingConfiguration, database_manager: DatabaseManager, settings=None, trading_config_file: str = "trading_config.json"):
        """
        初始化交易引擎
        
        Args:
            config: 交易配置參數（向後兼容）
            database_manager: 數據庫管理器
            settings: 系統設置（可選）
            trading_config_file: 交易配置文件路徑
        """
        self.legacy_config = config  # 保留舊配置以向後兼容
        self.database_manager = database_manager
        
        # 如果沒有提供settings，創建默認設置
        if settings is None:
            from ..config.settings import Settings
            settings = Settings()
        self.settings = settings
        
        # 載入新的交易配置系統
        self.config_manager = TradingConfigManager(trading_config_file)
        self.trading_config = self.config_manager.load_config()
        
        # 驗證配置
        config_errors = self.config_manager.validate_config()
        if config_errors:
            logger.warning(f"⚠️ 配置驗證發現問題: {config_errors}")
        
        logger.info(f"📋 交易配置已載入: {trading_config_file}")
        
        # 核心組件
        self.browser_manager = BrowserManager(settings)
        self.page_navigator = PageNavigator(self.browser_manager, settings)
        self.login_handler = LoginHandler(self.browser_manager, self.page_navigator, settings, database_manager)
        self.state_machine = StateMachine(settings)
        
        # 操作模組
        self.market_operations = MarketOperations(settings, self.browser_manager, self.page_navigator)
        self.inventory_manager = InventoryManager(settings, self.browser_manager, self.page_navigator)
        self.bank_operations = BankOperations(self.browser_manager)
        
        # 策略模組
        self.buying_strategy = BuyingStrategy(config, self.trading_config)
        self.selling_strategy = SellingStrategy(config, self.trading_config)
        
        # 詳細日誌記錄器
        self.trading_logger = TradingLogger()
        
        # 狀態追蹤
        self.current_session: Optional[TradingSessionData] = None
        self.last_resources_check: Optional[datetime] = None
        self.last_market_scan: Optional[datetime] = None
        self.retry_count = 0
        self.consecutive_errors = 0
        
        # 性能統計
        self.session_stats = {
            "total_purchases": 0,
            "total_sales": 0,
            "total_profit": 0.0,
            "successful_cycles": 0,
            "failed_cycles": 0,
        }
        
        logger.info("交易引擎初始化完成")

    async def start_trading_session(self) -> bool:
        """
        啟動交易會話
        
        Returns:
            是否成功啟動
        """
        try:
            logger.info("🚀 啟動交易會話")
            
            # 創建新的交易會話
            self.current_session = TradingSessionData(
                session_id="",
                start_time=datetime.now(),
                current_state=TradingState.INITIALIZING
            )
            
            # 初始化瀏覽器
            await self.browser_manager.initialize()
            
            # 初始化頁面導航器
            await self.page_navigator.initialize()
            
            # 設置初始狀態
            self.state_machine.set_state(TradingState.INITIALIZING)
            
            logger.info(f"✅ 交易會話啟動成功，會話ID: {self.current_session.session_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 啟動交易會話失敗: {e}")
            return False

    async def run_trading_cycle(self) -> bool:
        """
        執行一個完整的交易週期
        
        Returns:
            是否成功完成週期
        """
        # 開始新的交易週期記錄
        cycle_id = self.trading_logger.start_cycle()
        
        try:
            logger.info("🔄 開始交易週期")
            
            # 首先檢查登錄狀態 - 必須在訪問任何其他頁面之前完成
            if not await self._execute_login_check():
                self.trading_logger.record_error("登錄檢查失敗", "login")
                self.trading_logger.end_cycle(success=False)
                return False
            
            # 登錄成功後再檢查系統資源
            initial_resources = await self._execute_resource_check()
            if initial_resources:
                self.trading_logger.record_resource_snapshot(initial_resources, "before")
            
            # 檢查系統資源
            resources = initial_resources
            if not resources:
                self.trading_logger.record_error("資源檢查失敗", "resource_check")
                self.trading_logger.end_cycle(success=False)
                return False
            
            # 空間管理
            if not await self._execute_space_management(resources):
                self.trading_logger.record_error("空間管理失敗", "space_management")
                self.trading_logger.end_cycle(success=False)
                return False
            
            # 市場分析和即時購買（合併階段）
            market_condition = await self._execute_market_analysis_and_buying(resources)
            if not market_condition:
                self.trading_logger.record_error("市場分析和購買失敗", "market_analysis_buying")
                self.trading_logger.end_cycle(success=False)
                return False
            
            # 檢查是否因為庫存空間不足而需要立即進行空間管理
            if market_condition.market_activity_level == "space_management_required":
                logger.info("🔄 檢測到庫存空間不足，立即執行額外的空間管理")
                
                # 重新檢查資源狀態
                updated_resources = await self._execute_resource_check()
                if updated_resources:
                    resources = updated_resources
                
                # 執行額外的空間管理
                space_management_success = await self._execute_space_management(resources)
                if not space_management_success:
                    logger.warning("⚠️ 緊急空間管理失敗，但繼續執行銷售階段")
                else:
                    logger.info("✅ 緊急空間管理完成")
            
            # 執行銷售階段
            await self._execute_selling_phase(resources)
            
            # 記錄週期結束後的資源狀態
            final_resources = await self._execute_resource_check()
            if final_resources:
                self.trading_logger.record_resource_snapshot(final_resources, "after")
            
            # 更新統計
            self.session_stats["successful_cycles"] += 1
            self.consecutive_errors = 0
            
            # 結束週期記錄
            self.trading_logger.end_cycle(success=True)
            
            logger.info("✅ 交易週期完成")
            return True
            
        except Exception as e:
            logger.error(f"❌ 交易週期執行失敗: {e}")
            self.trading_logger.record_error(str(e), "trading_cycle")
            self.trading_logger.end_cycle(success=False)
            self.session_stats["failed_cycles"] += 1
            self.consecutive_errors += 1
            
            # 處理錯誤
            await self._handle_trading_error(e)
            return False

    async def _execute_login_check(self) -> bool:
        """執行登錄檢查"""
        self.trading_logger.start_stage("login")
        
        try:
            logger.info("🔐 檢查登錄狀態")
            self.state_machine.set_state(TradingState.LOGIN_REQUIRED)
            
            # 使用智能登錄
            login_success = await self.login_handler.smart_login()
            
            if login_success:
                logger.info("✅ 登錄狀態正常")
                self.trading_logger.end_stage("login", success=True)
                return True
            else:
                logger.warning("⚠️ 登錄失敗")
                self.current_session.login_failures += 1
                
                # 重試登錄
                if self.current_session.login_failures < self.trading_config.risk_management.max_login_retries:
                    wait_time = self.trading_config.risk_management.login_retry_wait_seconds
                    logger.info(f"🔄 等待 {wait_time} 秒後重試登錄")
                    self.trading_logger.record_wait("login_retry", wait_time, "登錄失敗重試")
                    await asyncio.sleep(wait_time)
                    self.trading_logger.end_stage("login", success=False)
                    return await self._execute_login_check()
                else:
                    logger.error("❌ 登錄重試次數已達上限")
                    self.state_machine.set_state(TradingState.LOGIN_FAILED)
                    self.trading_logger.end_stage("login", success=False)
                    return False
                    
        except Exception as e:
            logger.error(f"❌ 登錄檢查失敗: {e}")
            self.trading_logger.record_error(str(e), "login")
            self.trading_logger.end_stage("login", success=False)
            return False

    async def _execute_resource_check(self) -> Optional[SystemResources]:
        """執行資源檢查"""
        self.trading_logger.start_stage("resource_check")
        
        try:
            logger.info("💰 檢查系統資源")
            self.state_machine.set_state(TradingState.CHECKING_RESOURCES)
            
            # 首先檢查是否已登錄，如果沒有登錄則不要訪問需要登錄的頁面
            if not await self.page_navigator.check_login_status():
                logger.warning("⚠️ 用戶未登錄，無法檢查資源狀態")
                self.trading_logger.record_error("用戶未登錄", "resource_check")
                self.trading_logger.end_stage("resource_check", success=False)
                return None
            
            # 獲取當前現金
            current_cash = await self.page_navigator.get_current_cash()
            current_cash = current_cash or 0  # 處理 None 值
            
            # 獲取銀行餘額
            bank_balance = await self.bank_operations.get_bank_balance()
            bank_balance = bank_balance or 0  # 處理 None 值
            
            # 獲取庫存狀態
            inventory_status = await self.inventory_manager.get_inventory_status()
            if not inventory_status:
                logger.warning("⚠️ 無法獲取庫存狀態，使用默認值")
                inventory_used, inventory_total = 0, 26
            else:
                inventory_used = inventory_status.get('used', 0) if isinstance(inventory_status, dict) else inventory_status.current_count
                inventory_total = inventory_status.get('total', 26) if isinstance(inventory_status, dict) else inventory_status.max_capacity
            
            # 獲取倉庫狀態
            storage_status = await self.inventory_manager.get_storage_status()
            if not storage_status:
                logger.warning("⚠️ 無法獲取倉庫狀態，使用默認值")
                storage_used, storage_total = 0, 40
            else:
                storage_used = storage_status.get('used', 0) if isinstance(storage_status, dict) else storage_status.current_count
                storage_total = storage_status.get('total', 40) if isinstance(storage_status, dict) else storage_status.max_capacity
            
            # 獲取銷售位狀態
            selling_slots_status = await self.market_operations.get_selling_slots_status()
            if not selling_slots_status:
                logger.warning("⚠️ 無法獲取銷售位狀態，使用默認值")
                selling_slots_used, selling_slots_total = 0, 26
            else:
                selling_slots_used = selling_slots_status.current_listings
                selling_slots_total = selling_slots_status.max_slots
            
            # 創建資源狀況對象
            resources = SystemResources(
                current_cash=current_cash,
                bank_balance=bank_balance,
                total_funds=current_cash + bank_balance,
                inventory_used=inventory_used,
                inventory_total=inventory_total,
                storage_used=storage_used,
                storage_total=storage_total,
                selling_slots_used=selling_slots_used,
                selling_slots_total=selling_slots_total
            )
            
            logger.info(f"💰 資源檢查完成 - 總資金: ${resources.total_funds:,}, "
                       f"庫存: {resources.inventory_used}/{resources.inventory_total}, "
                       f"倉庫: {resources.storage_used}/{resources.storage_total}, "
                       f"銷售位: {resources.selling_slots_used}/{resources.selling_slots_total}")
            
            # 檢查是否需要從銀行提取資金
            if current_cash < 100000 and bank_balance > 0:
                withdraw_amount = bank_balance
                logger.info("💸 現金不足，從銀行提取資金")
                withdrawal_success = await self.bank_operations.withdraw_all_funds()
                
                if withdrawal_success:
                    self.trading_logger.record_withdrawal(withdraw_amount, success=True)
                    resources.current_cash = await self.page_navigator.get_current_cash()
                    resources.total_funds = resources.current_cash + resources.bank_balance
                else:
                    self.trading_logger.record_withdrawal(withdraw_amount, success=False)
            
            self.last_resources_check = datetime.now()
            self.trading_logger.end_stage("resource_check", success=True)
            return resources
            
        except Exception as e:
            logger.error(f"❌ 資源檢查失敗: {e}")
            self.trading_logger.record_error(str(e), "resource_check")
            self.trading_logger.end_stage("resource_check", success=False)
            return None

    async def _execute_space_management(self, resources: SystemResources) -> bool:
        """執行空間管理"""
        self.trading_logger.start_stage("space_management")
        
        try:
            logger.info("📦 執行空間管理")
            self.state_machine.set_state(TradingState.CHECKING_INVENTORY)
            
            # 檢查庫存是否需要整理
            if resources.inventory_space_available < 10:  # 庫存空間不足10個
                logger.info("📦 庫存空間不足，嘗試存儲到倉庫")
                
                if resources.storage_space_available > 0:
                    # 將物品存儲到倉庫
                    self.state_machine.set_state(TradingState.DEPOSITING_TO_STORAGE)
                    success = await self.inventory_manager.deposit_all_to_storage()
                    
                    if success:
                        logger.info("✅ 物品已存儲到倉庫")
                        item_count = resources.inventory_used
                        self.trading_logger.record_storage_operation("deposit", item_count, success=True)
                        # 重新檢查資源
                        updated_resources = await self._execute_resource_check()
                        if updated_resources:
                            resources.inventory_used = updated_resources.inventory_used
                            resources.storage_used = updated_resources.storage_used
                    else:
                        logger.warning("⚠️ 存儲到倉庫失敗")
                        item_count = resources.inventory_used
                        self.trading_logger.record_storage_operation("deposit", item_count, success=False)
                else:
                    logger.warning("⚠️ 倉庫空間也不足")
                    self.state_machine.set_state(TradingState.SPACE_FULL)
            
            self.trading_logger.end_stage("space_management", success=True)
            return True
            
        except Exception as e:
            logger.error(f"❌ 空間管理失敗: {e}")
            self.trading_logger.record_error(str(e), "space_management")
            self.trading_logger.end_stage("space_management", success=False)
            return False

    async def _execute_market_analysis_and_buying(self, resources: SystemResources) -> Optional[MarketCondition]:
        """執行市場分析和即時購買（修正版）"""
        self.trading_logger.start_stage("market_analysis")
        
        try:
            logger.info("📊 執行市場分析和即時購買")
            self.state_machine.set_state(TradingState.MARKET_SCANNING)
            
            # 獲取配置中的所有目標物品
            target_items = self.trading_config.market_search.target_items
            max_items_per_search = self.trading_config.market_search.max_items_per_search
            
            logger.info(f"🎯 逐一搜索並購買目標物品: {len(target_items)} 種物品")
            
            import time
            total_start_time = time.time()
            total_purchases = 0
            total_opportunities = 0
            all_profit_margins = []
            
            # 逐一搜索每種目標物品，並立即分析購買
            for i, target_item in enumerate(target_items, 1):
                try:
                    logger.info(f"🔍 第 {i}/{len(target_items)} 種物品: '{target_item}'")
                    
                    # 1. 搜索當前物品
                    scan_start_time = time.time()
                    market_items = await self.market_operations.scan_market_items(
                        search_term=target_item, 
                        max_items=max_items_per_search
                    )
                    scan_duration = time.time() - scan_start_time
                    
                    logger.info(f"✅ 找到 {len(market_items)} 個 '{target_item}' (耗時: {scan_duration:.1f}秒)")
                    self.trading_logger.record_market_scan(target_item, len(market_items), scan_duration)
                    
                    if not market_items:
                        logger.info(f"ℹ️ '{target_item}' 沒有可購買物品，跳過")
                        continue
                    
                    # 2. 立即分析當前物品的購買機會
                    purchase_opportunities = await self.buying_strategy.evaluate_market_items(
                        market_items, resources
                    )
                    
                    if not purchase_opportunities:
                        logger.info(f"ℹ️ '{target_item}' 沒有值得購買的機會")
                        continue
                    
                    # 3. 立即購買當前物品（趁頁面還顯示該物品）
                    logger.info(f"🛒 開始購買 '{target_item}' 物品")
                    
                    # 持續購買直到沒有值得購買的機會
                    purchased_count = 0
                    max_purchases_per_item = 10  # 每種物品最多購買10次，避免無限循環
                    
                    while purchased_count < max_purchases_per_item:
                        # 重新掃描當前物品（因為購買後列表會刷新）
                        if purchased_count > 0:
                            logger.info(f"🔄 購買完成後重新掃描 '{target_item}'...")
                            current_market_items = await self.market_operations.scan_market_items(
                                search_term=target_item, 
                                max_items=max_items_per_search
                            )
                            
                            if not current_market_items:
                                logger.info(f"ℹ️ '{target_item}' 重新掃描後沒有物品，停止購買")
                                break
                            
                            # 重新評估購買機會
                            current_opportunities = await self.buying_strategy.evaluate_market_items(
                                current_market_items, resources
                            )
                            
                            if not current_opportunities:
                                logger.info(f"ℹ️ '{target_item}' 重新評估後沒有值得購買的機會，停止購買")
                                break
                        else:
                            current_opportunities = purchase_opportunities
                        
                        # 購買第一個機會（最低價）
                        if current_opportunities:
                            opportunity = current_opportunities[0]  # 總是選擇第一個（最低價）
                            
                            try:
                                logger.info(f"🛒 購買 {purchased_count + 1}: {opportunity.item.item_name} - "
                                           f"${opportunity.item.price} - 利潤率: {opportunity.profit_potential:.1%}")
                                
                                # 執行購買（此時頁面顯示的正是該物品）
                                purchase_result = await self.market_operations.execute_purchase(opportunity.item)
                                
                                if purchase_result.get('success'):
                                    purchased_count += 1
                                    total_purchases += 1
                                    self.session_stats["total_purchases"] += 1
                                    self.buying_strategy.record_purchase(opportunity)
                                    all_profit_margins.append(opportunity.profit_potential)
                                    
                                    # 使用實際購買信息記錄
                                    actual_unit_price = purchase_result.get('unit_price', opportunity.item.price)
                                    actual_quantity = purchase_result.get('quantity', opportunity.item.quantity)
                                    actual_total_price = purchase_result.get('total_price', actual_unit_price * actual_quantity)
                                    actual_seller = purchase_result.get('seller', opportunity.item.seller)
                                    
                                    self.trading_logger.record_purchase(
                                        item_name=purchase_result.get('item_name', opportunity.item.item_name),
                                        quantity=actual_quantity,
                                        unit_price=actual_unit_price,
                                        total_price=actual_total_price,
                                        success=True,
                                        details={
                                            "seller": actual_seller,
                                            "profit_potential": opportunity.profit_potential,
                                            "priority_score": opportunity.priority_score,
                                            "expected_unit_price": opportunity.item.price,
                                            "price_difference": purchase_result.get('price_difference', 0.0)
                                        }
                                    )
                                    
                                    logger.info(f"✅ 購買成功: {opportunity.item.item_name} (第{purchased_count}次) - "
                                               f"實際單價: ${actual_unit_price:.2f}, 總價: ${actual_total_price:.2f}")
                                    
                                    # 更新資源狀況（使用實際花費）
                                    resources.current_cash -= actual_total_price
                                    resources.total_funds = resources.current_cash + resources.bank_balance
                                    
                                    # 檢查空間和資金限制
                                    if resources.inventory_space_available <= 5:
                                        logger.info("📦 庫存空間不足，停止購買")
                                        break
                                    if resources.current_cash < 10000:
                                        logger.info("💰 現金不足，停止購買")
                                        break
                                        
                                    # 短暫延遲讓頁面更新
                                    await asyncio.sleep(2)
                                else:
                                    # 購買失敗，記錄失敗原因
                                    failure_reason = purchase_result.get('reason', '未知原因')
                                    
                                    # 特別處理庫存空間不足的情況
                                    if purchase_result.get('requires_space_management'):
                                        inventory_used = purchase_result.get('inventory_used', 0)
                                        inventory_total = purchase_result.get('inventory_total', 26)
                                        
                                        logger.warning(f"🚨 庫存空間不足: {inventory_used}/{inventory_total}，立即停止所有購買並轉向空間管理")
                                        
                                        # 記錄庫存滿的購買失敗
                                        total_cost = opportunity.item.price * opportunity.item.quantity
                                        self.trading_logger.record_purchase(
                                            item_name=opportunity.item.item_name,
                                            quantity=opportunity.item.quantity,
                                            unit_price=opportunity.item.price,
                                            total_price=total_cost,
                                            success=False,
                                            details={
                                                "reason": "庫存空間不足",
                                                "inventory_used": inventory_used,
                                                "inventory_total": inventory_total,
                                                "requires_space_management": True
                                            }
                                        )
                                        
                                        # 立即返回特殊狀態，觸發空間管理
                                        logger.info("🔄 由於庫存空間不足，提前結束市場分析階段，準備執行空間管理")
                                        
                                        # 創建特殊的市場狀況報告，表明需要空間管理
                                        from src.dfautotrans.data.models import MarketCondition
                                        from datetime import datetime
                                        market_condition = MarketCondition(
                                            valuable_opportunities=total_opportunities,
                                            average_profit_margin=sum(all_profit_margins) / len(all_profit_margins) if all_profit_margins else 0,
                                            market_activity_level="space_management_required",
                                            total_items_scanned=len(target_items),
                                            last_scan_time=datetime.now()
                                        )
                                        
                                        self.last_market_scan = datetime.now()
                                        self.trading_logger.end_stage("market_analysis", success=True, 
                                                                    details={"interrupted_reason": "inventory_full"})
                                        return market_condition
                                    
                                    # 其他購買失敗情況
                                    total_cost = opportunity.item.price * opportunity.item.quantity
                                    self.trading_logger.record_purchase(
                                        item_name=opportunity.item.item_name,
                                        quantity=opportunity.item.quantity,
                                        unit_price=opportunity.item.price,
                                        total_price=total_cost,
                                        success=False,
                                        details={"reason": failure_reason}
                                    )
                                    logger.warning(f"⚠️ 購買失敗，停止購買 '{target_item}': {opportunity.item.item_name} - 原因: {failure_reason}")
                                    break
                                    
                            except Exception as e:
                                logger.warning(f"⚠️ 購買 {opportunity.item.item_name} 時出錯: {e}")
                                break
                        else:
                            logger.info(f"ℹ️ '{target_item}' 沒有可購買的機會")
                            break
                    
                    if purchased_count > 0:
                        logger.info(f"🎉 '{target_item}' 購買完成，總共購買了 {purchased_count} 次")
                    
                    total_opportunities += len(purchase_opportunities)
                    
                    # 檢查是否需要停止（資金或空間不足）
                    if resources.current_cash < 10000 or resources.inventory_space_available <= 5:
                        logger.info("💰📦 資金或空間不足，提前結束市場分析")
                        break
                    
                    # 短暫延遲避免過於頻繁的操作
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.warning(f"⚠️ 處理 '{target_item}' 時出錯: {e}")
                    continue
            
            total_duration = time.time() - total_start_time
            avg_profit_margin = sum(all_profit_margins) / len(all_profit_margins) if all_profit_margins else 0
            
            logger.info(f"📊 市場分析和購買完成 - 成功購買: {total_purchases}, "
                       f"總機會: {total_opportunities}, 平均利潤率: {avg_profit_margin:.1%}, "
                       f"總耗時: {total_duration:.1f}秒")
            
            # 生成市場狀況報告
            from src.dfautotrans.data.models import MarketCondition
            from datetime import datetime
            market_condition = MarketCondition(
                valuable_opportunities=total_opportunities,
                average_profit_margin=avg_profit_margin,
                market_activity_level="high" if total_opportunities > 10 else "medium" if total_opportunities > 5 else "low",
                total_items_scanned=len(target_items),
                last_scan_time=datetime.now()
            )
            
            self.last_market_scan = datetime.now()
            self.trading_logger.end_stage("market_analysis", success=True)
            return market_condition
            
        except Exception as e:
            logger.error(f"❌ 市場分析和購買失敗: {e}")
            self.trading_logger.record_error(str(e), "market_analysis")
            self.trading_logger.end_stage("market_analysis", success=False)
            return None



    async def _execute_selling_phase(self, resources: SystemResources) -> bool:
        """執行銷售階段（優化版）"""
        self.trading_logger.start_stage("selling")
        
        try:
            logger.info("💰 執行銷售階段")
            self.state_machine.set_state(TradingState.SELLING)
            
            # 獲取庫存物品
            inventory_items = await self.inventory_manager.get_inventory_items()
            
            if not inventory_items:
                logger.info("ℹ️ 沒有庫存物品可供銷售")
                return True
            
            # 獲取銷售位狀態
            selling_slots_status = await self.market_operations.get_selling_slots_status()
            
            if selling_slots_status.available_slots <= 0:
                logger.info("ℹ️ 沒有可用的銷售位")
                return True
            
            # 制定銷售策略
            sell_orders = await self.selling_strategy.plan_selling_strategy(
                inventory_items, selling_slots_status, resources
            )
            
            if not sell_orders:
                logger.info("ℹ️ 沒有物品需要銷售")
                return True
            
            logger.info(f"💰 計劃銷售 {len(sell_orders)} 個物品")
            
            # 使用批量上架功能 - 避免重複導航
            if hasattr(self.market_operations, 'batch_list_items_for_sale'):
                logger.info("📦 使用批量上架功能...")
                results = await self.market_operations.batch_list_items_for_sale(sell_orders)
                
                # 統計結果
                successful_sales = sum(results)
                for i, (sell_order, success) in enumerate(zip(sell_orders, results), 1):
                    if success:
                        self.session_stats["total_sales"] += 1
                        self.selling_strategy.record_sale(sell_order)
                        
                        # 記錄銷售操作到詳細日誌
                        total_price = sell_order.price * sell_order.quantity
                        self.trading_logger.record_sale(
                            item_name=sell_order.item.item_name,
                            quantity=sell_order.quantity,
                            unit_price=sell_order.price,
                            total_price=total_price,
                            success=True,
                            details={
                                "pricing_strategy": sell_order.pricing_strategy,
                                "profit_margin": getattr(sell_order, 'profit_margin', 0)
                            }
                        )
                        
                        logger.info(f"✅ 第 {i} 個物品銷售成功: {sell_order.item.item_name}")
                    else:
                        # 記錄銷售失敗
                        total_price = sell_order.price * sell_order.quantity
                        self.trading_logger.record_sale(
                            item_name=sell_order.item.item_name,
                            quantity=sell_order.quantity,
                            unit_price=sell_order.price,
                            total_price=total_price,
                            success=False,
                            details={"reason": "銷售操作失敗"}
                        )
                        logger.warning(f"⚠️ 第 {i} 個物品銷售失敗: {sell_order.item.item_name}")
            else:
                # 降級到單個上架（保持向後兼容）
                logger.info("🔄 使用單個上架模式...")
                successful_sales = 0
                for i, sell_order in enumerate(sell_orders, 1):
                    try:
                        logger.info(f"💰 銷售第 {i}/{len(sell_orders)} 個物品: {sell_order.item.item_name} - "
                                   f"價格: ${sell_order.selling_price}")
                        
                        success = await self.market_operations.list_item_for_sale(
                            sell_order.item.item_name, sell_order.selling_price
                        )
                        
                        if success:
                            successful_sales += 1
                            self.session_stats["total_sales"] += 1
                            self.selling_strategy.record_sale(sell_order)
                            logger.info(f"✅ 第 {i} 個物品銷售成功: {sell_order.item.item_name}")
                        else:
                            logger.warning(f"⚠️ 第 {i} 個物品銷售失敗: {sell_order.item.item_name}")
                            
                    except Exception as e:
                        logger.warning(f"⚠️ 銷售第 {i} 個物品時出錯 {sell_order.item.item_name}: {e}")
                        continue
            
            logger.info(f"💰 銷售階段完成，成功銷售 {successful_sales}/{len(sell_orders)} 個物品")
            self.trading_logger.end_stage("selling", success=True)
            return True
            
        except Exception as e:
            logger.error(f"❌ 銷售階段失敗: {e}")
            self.trading_logger.record_error(str(e), "selling")
            self.trading_logger.end_stage("selling", success=False)
            return False

    async def _handle_trading_error(self, error: Exception):
        """處理交易錯誤"""
        try:
            logger.error(f"🚨 處理交易錯誤: {error}")
            self.state_machine.set_state(TradingState.ERROR)
            
            # 增加錯誤計數
            if self.current_session:
                if "network" in str(error).lower() or "timeout" in str(error).lower():
                    self.current_session.network_errors += 1
                else:
                    self.current_session.business_errors += 1
            
            # 根據連續錯誤次數決定等待時間
            if self.consecutive_errors >= 3:
                logger.warning("⚠️ 連續錯誤過多，進入長時間等待")
                self.state_machine.set_state(TradingState.CRITICAL_ERROR)
                await asyncio.sleep(self.trading_config.risk_management.blocked_wait_seconds)
            else:
                await asyncio.sleep(30)  # 短暫等待後重試
                
        except Exception as e:
            logger.error(f"❌ 錯誤處理失敗: {e}")

    async def wait_for_next_cycle(self, resources: SystemResources):
        """等待下一個交易週期"""
        try:
            # 決定等待時間
            if resources.is_completely_blocked:
                wait_time = self.trading_config.risk_management.blocked_wait_seconds
                logger.info(f"⏸️ 系統完全阻塞，等待 {wait_time} 秒")
                self.trading_logger.record_wait("cycle_blocked", wait_time, "系統阻塞等待")
                self.state_machine.set_state(TradingState.WAITING_BLOCKED)
                await asyncio.sleep(wait_time)
            else:
                wait_time = self.trading_config.risk_management.normal_wait_seconds
                logger.info(f"⏸️ 正常等待 {wait_time} 秒")
                self.trading_logger.record_wait("cycle_normal", wait_time, "正常週期間隔等待")
                self.state_machine.set_state(TradingState.WAITING_NORMAL)
                await asyncio.sleep(wait_time)
                
        except Exception as e:
            logger.error(f"❌ 等待過程中出錯: {e}")
            self.trading_logger.record_error(str(e), "wait")

    async def stop_trading_session(self):
        """停止交易會話"""
        try:
            logger.info("🛑 停止交易會話")
            
            if self.current_session:
                self.current_session.end_time = datetime.now()
                self.current_session.current_state = TradingState.IDLE
            
            # 關閉瀏覽器
            await self.browser_manager.cleanup()
            
            # 輸出會話統計
            self._log_session_summary()
            
            logger.info("✅ 交易會話已停止")
            
        except Exception as e:
            logger.error(f"❌ 停止交易會話失敗: {e}")

    def _log_session_summary(self):
        """輸出會話總結"""
        if not self.current_session:
            return
            
        duration = (self.current_session.end_time - self.current_session.start_time).total_seconds() / 3600
        
        logger.info("📊 交易會話總結:")
        logger.info(f"   會話時長: {duration:.1f} 小時")
        logger.info(f"   成功週期: {self.session_stats['successful_cycles']}")
        logger.info(f"   失敗週期: {self.session_stats['failed_cycles']}")
        logger.info(f"   總購買次數: {self.session_stats['total_purchases']}")
        logger.info(f"   總銷售次數: {self.session_stats['total_sales']}")
        logger.info(f"   登錄失敗: {self.current_session.login_failures}")
        logger.info(f"   網絡錯誤: {self.current_session.network_errors}")
        logger.info(f"   業務錯誤: {self.current_session.business_errors}")

    def get_current_status(self) -> Dict[str, any]:
        """獲取當前狀態信息"""
        return {
            "current_state": self.state_machine.current_state.value if self.state_machine.current_state else "unknown",
            "session_active": self.current_session is not None,
            "session_stats": self.session_stats.copy(),
            "last_resources_check": self.last_resources_check.isoformat() if self.last_resources_check else None,
            "last_market_scan": self.last_market_scan.isoformat() if self.last_market_scan else None,
            "consecutive_errors": self.consecutive_errors,
        } 