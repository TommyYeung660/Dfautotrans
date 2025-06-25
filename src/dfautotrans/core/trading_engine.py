"""
Dead Frontier 自動交易系統 - 核心交易引擎

這是系統的核心模組，負責協調所有子系統並執行完整的交易週期。
"""

import asyncio
import logging
from typing import Optional, Dict, List
from datetime import datetime, timedelta

from ..data.models import (
    TradingState, TradingCycle, TradingSession, TradingConfiguration,
    SystemResources, MarketCondition, PurchaseOpportunity, SellOrder
)
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

logger = logging.getLogger(__name__)


class TradingEngine:
    """Dead Frontier 自動交易引擎核心類"""
    
    def __init__(self, config: TradingConfiguration, database_manager: DatabaseManager, settings=None):
        """
        初始化交易引擎
        
        Args:
            config: 交易配置參數
            database_manager: 數據庫管理器
            settings: 系統設置（可選）
        """
        self.config = config
        self.database_manager = database_manager
        
        # 如果沒有提供settings，創建默認設置
        if settings is None:
            from ..config.settings import Settings
            settings = Settings()
        self.settings = settings
        
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
        self.buying_strategy = BuyingStrategy(config)
        self.selling_strategy = SellingStrategy(config)
        
        # 狀態追蹤
        self.current_session: Optional[TradingSession] = None
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
            self.current_session = TradingSession(
                session_id="",
                start_time=datetime.now(),
                current_state=TradingState.INITIALIZING
            )
            
            # 初始化瀏覽器
            await self.browser_manager.initialize()
            
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
        try:
            logger.info("🔄 開始交易週期")
            
            # 檢查登錄狀態
            if not await self._execute_login_check():
                return False
            
            # 檢查系統資源
            resources = await self._execute_resource_check()
            if not resources:
                return False
            
            # 空間管理
            if not await self._execute_space_management(resources):
                return False
            
            # 市場分析和交易
            market_condition = await self._execute_market_analysis(resources)
            if not market_condition:
                return False
            
            # 執行購買階段
            if market_condition.valuable_opportunities > 0:
                await self._execute_buying_phase(resources)
            
            # 執行銷售階段
            await self._execute_selling_phase(resources)
            
            # 更新統計
            self.session_stats["successful_cycles"] += 1
            self.consecutive_errors = 0
            
            logger.info("✅ 交易週期完成")
            return True
            
        except Exception as e:
            logger.error(f"❌ 交易週期執行失敗: {e}")
            self.session_stats["failed_cycles"] += 1
            self.consecutive_errors += 1
            
            # 處理錯誤
            await self._handle_trading_error(e)
            return False

    async def _execute_login_check(self) -> bool:
        """執行登錄檢查"""
        try:
            logger.info("🔐 檢查登錄狀態")
            self.state_machine.set_state(TradingState.LOGIN_REQUIRED)
            
            # 使用智能登錄
            login_success = await self.login_handler.smart_login()
            
            if login_success:
                logger.info("✅ 登錄狀態正常")
                return True
            else:
                logger.warning("⚠️ 登錄失敗")
                self.current_session.login_failures += 1
                
                # 重試登錄
                if self.current_session.login_failures < self.config.max_login_retries:
                    logger.info(f"🔄 等待 {self.config.login_retry_wait_seconds} 秒後重試登錄")
                    await asyncio.sleep(self.config.login_retry_wait_seconds)
                    return await self._execute_login_check()
                else:
                    logger.error("❌ 登錄重試次數已達上限")
                    self.state_machine.set_state(TradingState.LOGIN_FAILED)
                    return False
                    
        except Exception as e:
            logger.error(f"❌ 登錄檢查失敗: {e}")
            return False

    async def _execute_resource_check(self) -> Optional[SystemResources]:
        """執行資源檢查"""
        try:
            logger.info("💰 檢查系統資源")
            self.state_machine.set_state(TradingState.CHECKING_RESOURCES)
            
            # 獲取當前現金
            current_cash = await self.page_navigator.get_current_cash()
            
            # 獲取銀行餘額
            bank_balance = await self.bank_operations.get_bank_balance()
            
            # 獲取庫存狀態
            inventory_status = await self.inventory_manager.get_inventory_status()
            
            # 獲取倉庫狀態
            storage_status = await self.inventory_manager.get_storage_status()
            
            # 獲取銷售位狀態
            selling_slots_status = await self.market_operations.get_selling_slots_status()
            
            # 創建資源狀況對象
            resources = SystemResources(
                current_cash=current_cash,
                bank_balance=bank_balance,
                total_funds=current_cash + bank_balance,
                inventory_used=inventory_status.current_count,
                inventory_total=inventory_status.max_capacity,
                storage_used=storage_status.current_count,
                storage_total=storage_status.max_capacity,
                selling_slots_used=selling_slots_status.current_listings,
                selling_slots_total=selling_slots_status.max_slots
            )
            
            logger.info(f"💰 資源檢查完成 - 總資金: ${resources.total_funds:,}, "
                       f"庫存: {resources.inventory_used}/{resources.inventory_total}, "
                       f"倉庫: {resources.storage_used}/{resources.storage_total}, "
                       f"銷售位: {resources.selling_slots_used}/{resources.selling_slots_total}")
            
            # 檢查是否需要從銀行提取資金
            if current_cash < 10000 and bank_balance > 0:
                logger.info("💸 現金不足，從銀行提取資金")
                await self.bank_operations.withdraw_all_funds()
                resources.current_cash = await self.page_navigator.get_current_cash()
                resources.total_funds = resources.current_cash + resources.bank_balance
            
            self.last_resources_check = datetime.now()
            return resources
            
        except Exception as e:
            logger.error(f"❌ 資源檢查失敗: {e}")
            return None

    async def _execute_space_management(self, resources: SystemResources) -> bool:
        """執行空間管理"""
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
                        # 重新檢查資源
                        updated_resources = await self._execute_resource_check()
                        if updated_resources:
                            resources.inventory_used = updated_resources.inventory_used
                            resources.storage_used = updated_resources.storage_used
                    else:
                        logger.warning("⚠️ 存儲到倉庫失敗")
                else:
                    logger.warning("⚠️ 倉庫空間也不足")
                    self.state_machine.set_state(TradingState.SPACE_FULL)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 空間管理失敗: {e}")
            return False

    async def _execute_market_analysis(self, resources: SystemResources) -> Optional[MarketCondition]:
        """執行市場分析"""
        try:
            logger.info("📊 執行市場分析")
            self.state_machine.set_state(TradingState.MARKET_SCANNING)
            
            # 掃描市場物品
            market_items = await self.market_operations.scan_market_items()
            logger.info(f"🔍 掃描到 {len(market_items)} 個市場物品")
            
            # 使用購買策略評估物品
            purchase_opportunities = await self.buying_strategy.evaluate_market_items(
                market_items, resources
            )
            
            # 生成市場狀況報告
            market_condition = self.buying_strategy.get_market_condition_assessment(
                purchase_opportunities
            )
            
            logger.info(f"📊 市場分析完成 - 有價值機會: {market_condition.valuable_opportunities}, "
                       f"平均利潤率: {market_condition.average_profit_margin:.1%}, "
                       f"活躍度: {market_condition.market_activity_level}")
            
            self.last_market_scan = datetime.now()
            return market_condition
            
        except Exception as e:
            logger.error(f"❌ 市場分析失敗: {e}")
            return None

    async def _execute_buying_phase(self, resources: SystemResources) -> bool:
        """執行購買階段"""
        try:
            logger.info("🛒 執行購買階段")
            self.state_machine.set_state(TradingState.BUYING)
            
            # 獲取購買機會
            market_items = await self.market_operations.scan_market_items()
            purchase_opportunities = await self.buying_strategy.evaluate_market_items(
                market_items, resources
            )
            
            if not purchase_opportunities:
                logger.info("ℹ️ 沒有值得購買的物品")
                return True
            
            # 執行購買
            successful_purchases = 0
            for opportunity in purchase_opportunities[:5]:  # 限制每次最多購買5個物品
                try:
                    logger.info(f"🛒 嘗試購買: {opportunity.item.item_name} - "
                               f"價格: ${opportunity.item.price} - "
                               f"利潤率: {opportunity.profit_potential:.1%}")
                    
                    success = await self.market_operations.execute_purchase(opportunity.item)
                    
                    if success:
                        successful_purchases += 1
                        self.session_stats["total_purchases"] += 1
                        self.buying_strategy.record_purchase(opportunity)
                        logger.info(f"✅ 購買成功: {opportunity.item.item_name}")
                        
                        # 更新資源狀況
                        resources.current_cash -= opportunity.item.price * opportunity.item.quantity
                        resources.total_funds = resources.current_cash + resources.bank_balance
                        
                        # 檢查空間限制
                        if resources.inventory_space_available <= 5:
                            logger.info("📦 庫存空間不足，停止購買")
                            break
                    else:
                        logger.warning(f"⚠️ 購買失敗: {opportunity.item.item_name}")
                        
                except Exception as e:
                    logger.warning(f"⚠️ 購買物品時出錯 {opportunity.item.item_name}: {e}")
                    continue
            
            logger.info(f"🛒 購買階段完成，成功購買 {successful_purchases} 個物品")
            return True
            
        except Exception as e:
            logger.error(f"❌ 購買階段失敗: {e}")
            return False

    async def _execute_selling_phase(self, resources: SystemResources) -> bool:
        """執行銷售階段"""
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
            
            # 執行銷售
            successful_sales = 0
            for sell_order in sell_orders:
                try:
                    logger.info(f"💰 嘗試銷售: {sell_order.item.item_name} - "
                               f"價格: ${sell_order.selling_price}")
                    
                    success = await self.market_operations.list_item_for_sale(
                        sell_order.item, sell_order.selling_price
                    )
                    
                    if success:
                        successful_sales += 1
                        self.session_stats["total_sales"] += 1
                        self.selling_strategy.record_sale(sell_order)
                        logger.info(f"✅ 銷售成功: {sell_order.item.item_name}")
                    else:
                        logger.warning(f"⚠️ 銷售失敗: {sell_order.item.item_name}")
                        
                except Exception as e:
                    logger.warning(f"⚠️ 銷售物品時出錯 {sell_order.item.item_name}: {e}")
                    continue
            
            logger.info(f"💰 銷售階段完成，成功銷售 {successful_sales} 個物品")
            return True
            
        except Exception as e:
            logger.error(f"❌ 銷售階段失敗: {e}")
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
                await asyncio.sleep(self.config.blocked_wait_seconds)
            else:
                await asyncio.sleep(30)  # 短暫等待後重試
                
        except Exception as e:
            logger.error(f"❌ 錯誤處理失敗: {e}")

    async def wait_for_next_cycle(self, resources: SystemResources):
        """等待下一個交易週期"""
        try:
            # 決定等待時間
            if resources.is_completely_blocked:
                logger.info(f"⏸️ 系統完全阻塞，等待 {self.config.blocked_wait_seconds} 秒")
                self.state_machine.set_state(TradingState.WAITING_BLOCKED)
                await asyncio.sleep(self.config.blocked_wait_seconds)
            else:
                logger.info(f"⏸️ 正常等待 {self.config.normal_wait_seconds} 秒")
                self.state_machine.set_state(TradingState.WAITING_NORMAL)
                await asyncio.sleep(self.config.normal_wait_seconds)
                
        except Exception as e:
            logger.error(f"❌ 等待過程中出錯: {e}")

    async def stop_trading_session(self):
        """停止交易會話"""
        try:
            logger.info("🛑 停止交易會話")
            
            if self.current_session:
                self.current_session.end_time = datetime.now()
                self.current_session.current_state = TradingState.IDLE
            
            # 關閉瀏覽器
            await self.browser_manager.close()
            
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