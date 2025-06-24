# Dead Frontier 自動交易系統 - Python 架構設計

## 📁 項目結構

```
dfautotrans/
├── requirements.txt              # 依賴管理
├── pyproject.toml               # 項目配置
├── README.md                    # 項目文檔
├── .env.example                 # 環境變量範例
├── docker-compose.yml           # Docker 部署
├── main.py                      # 主程序入口
│
├── dfautotrans/                 # 主包
│   ├── __init__.py
│   ├── app.py                   # 應用程序主類
│   ├── cli.py                   # 命令行界面
│   │
│   ├── core/                    # 核心業務邏輯
│   │   ├── __init__.py
│   │   ├── browser_manager.py   # 瀏覽器會話管理
│   │   ├── market_analyzer.py   # 市場分析引擎
│   │   ├── inventory_manager.py # 庫存管理系統
│   │   ├── trade_executor.py    # 交易執行引擎
│   │   ├── risk_manager.py      # 風險管理系統
│   │   ├── price_calculator.py  # 價格計算器
│   │   └── session_manager.py   # 會話狀態管理
│   │
│   ├── automation/              # 自動化模組
│   │   ├── __init__.py
│   │   ├── anti_detection.py    # 反檢測系統
│   │   ├── human_behavior.py    # 人類行為模擬
│   │   ├── page_navigator.py    # 頁面導航器
│   │   ├── element_locator.py   # 元素定位器
│   │   └── action_performer.py  # 動作執行器
│   │
│   ├── data/                    # 數據層
│   │   ├── __init__.py
│   │   ├── database.py          # 數據庫連接
│   │   ├── models.py            # 數據模型
│   │   ├── repositories.py      # 數據倉庫模式
│   │   └── migrations/          # 數據庫遷移
│   │
│   ├── config/                  # 配置管理
│   │   ├── __init__.py
│   │   ├── settings.py          # 主配置文件
│   │   ├── items.py             # 商品配置
│   │   ├── strategies.py        # 交易策略配置
│   │   └── validation.py        # 配置驗證
│   │
│   ├── utils/                   # 工具模組
│   │   ├── __init__.py
│   │   ├── logger.py            # 日誌系統
│   │   ├── cache.py             # 緩存管理
│   │   ├── helpers.py           # 輔助函數
│   │   └── decorators.py        # 裝飾器
│   │
│   ├── strategies/              # 交易策略
│   │   ├── __init__.py
│   │   ├── base_strategy.py     # 基礎策略類
│   │   ├── buy_low_sell_high.py # 低買高賣策略
│   │   ├── arbitrage.py         # 套利策略
│   │   └── inventory_turnover.py # 庫存周轉策略
│   │
│   └── api/                     # API 接口 (可選)
│       ├── __init__.py
│       ├── routes.py            # 路由定義
│       ├── handlers.py          # 請求處理器
│       └── schemas.py           # API 模式
│
├── tests/                       # 測試代碼
│   ├── __init__.py
│   ├── conftest.py              # 測試配置
│   ├── unit/                    # 單元測試
│   ├── integration/             # 集成測試
│   └── e2e/                     # 端到端測試
│
├── scripts/                     # 腳本工具
│   ├── setup_database.py       # 數據庫初始化
│   ├── backup_data.py           # 數據備份
│   └── migration_tools.py       # 遷移工具
│
├── docs/                        # 文檔
│   ├── api.md                   # API 文檔
│   ├── deployment.md            # 部署指南
│   └── strategy_guide.md        # 策略指南
│
└── deployment/                  # 部署配置
    ├── Dockerfile
    ├── docker-compose.prod.yml
    ├── nginx.conf
    └── systemd/
```

## 🏗️ 核心架構設計

### 1. 應用程序主類

```python
# dfautotrans/app.py
import asyncio
import signal
from typing import Optional
from datetime import datetime, timedelta

from .core.browser_manager import BrowserManager
from .core.market_analyzer import MarketAnalyzer
from .core.inventory_manager import InventoryManager
from .core.trade_executor import TradeExecutor
from .core.risk_manager import RiskManager
from .core.session_manager import SessionManager
from .config.settings import Settings
from .utils.logger import get_logger

class DeadFrontierAutoTrader:
    """Dead Frontier 自動交易系統主類"""
    
    def __init__(self, config: Settings):
        self.config = config
        self.logger = get_logger(__name__)
        self.is_running = False
        self.shutdown_event = asyncio.Event()
        
        # 核心組件初始化
        self.browser_manager = BrowserManager(config.browser)
        self.session_manager = SessionManager(config.session)
        self.market_analyzer = MarketAnalyzer(config.market)
        self.inventory_manager = InventoryManager(config.inventory)
        self.trade_executor = TradeExecutor(config.trading)
        self.risk_manager = RiskManager(config.risk)
        
        # 設置信號處理
        self._setup_signal_handlers()
    
    async def start(self):
        """啟動自動交易系統"""
        try:
            self.logger.info("🚀 啟動 Dead Frontier 自動交易系統")
            self.is_running = True
            
            # 初始化組件
            await self._initialize_components()
            
            # 主運行循環
            await self._main_loop()
            
        except Exception as e:
            self.logger.error(f"❌ 系統啟動失敗: {e}")
            await self.shutdown()
            raise
    
    async def _main_loop(self):
        """主要業務循環"""
        while self.is_running and not self.shutdown_event.is_set():
            try:
                cycle_start = datetime.now()
                
                # 1. 會話狀態檢查
                if not await self.session_manager.is_session_valid():
                    await self.session_manager.refresh_session()
                
                # 2. 市場分析
                market_data = await self.market_analyzer.analyze_market()
                
                # 3. 庫存檢查
                inventory_status = await self.inventory_manager.check_inventory()
                
                # 4. 風險評估
                risk_assessment = await self.risk_manager.assess_current_risk()
                
                # 5. 交易決策執行
                if risk_assessment.allow_trading:
                    if inventory_status.should_sell:
                        await self._execute_sell_cycle(inventory_status)
                    
                    if inventory_status.can_buy and market_data.has_opportunities:
                        await self._execute_buy_cycle(market_data)
                
                # 6. 等待下一輪
                await self._wait_next_cycle()
                
            except Exception as e:
                self.logger.error(f"❌ 主循環錯誤: {e}")
                await self._handle_error(e)
    
    async def shutdown(self):
        """優雅關閉系統"""
        self.logger.info("🛑 正在關閉系統...")
        self.is_running = False
        self.shutdown_event.set()
        
        # 關閉所有組件
        await self.browser_manager.close()
```

### 2. 瀏覽器管理器

```python
# dfautotrans/core/browser_manager.py
import asyncio
from typing import Optional, Dict, Any
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from ..automation.anti_detection import AntiDetectionManager
from ..utils.logger import get_logger

class BrowserManager:
    """瀏覽器會話和頁面管理"""
    
    def __init__(self, config):
        self.config = config
        self.logger = get_logger(__name__)
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.anti_detection = AntiDetectionManager(config.anti_detection)
    
    async def initialize(self):
        """初始化瀏覽器"""
        self.playwright = await async_playwright().start()
        
        # 瀏覽器配置
        browser_config = {
            'headless': self.config.headless,
            'slow_mo': self.config.slow_mo,
            'args': self._get_browser_args(),
        }
        
        self.browser = await self.playwright.chromium.launch(**browser_config)
        
        # 創建上下文（應用反檢測配置）
        context_config = await self.anti_detection.get_context_config()
        self.context = await self.browser.new_context(**context_config)
        
        # 設置頁面攔截器
        await self._setup_page_interceptors()
        
        # 創建主頁面
        self.page = await self.context.new_page()
        
        # 應用反檢測腳本
        await self.anti_detection.inject_scripts(self.page)
        
        self.logger.info("✅ 瀏覽器初始化完成")
    
    async def navigate_to_marketplace(self) -> bool:
        """導航到市場頁面"""
        try:
            marketplace_url = "https://fairview.deadfrontier.com/onlinezombiemmo/index.php?page=35"
            
            # 人性化導航
            await self.anti_detection.simulate_navigation(self.page, marketplace_url)
            
            # 等待頁面加載
            await self.page.wait_for_load_state('domcontentloaded')
            await asyncio.sleep(2)  # 額外等待
            
            # 驗證頁面
            current_url = self.page.url
            if 'page=35' in current_url:
                self.logger.info("✅ 成功導航到市場頁面")
                return True
            else:
                self.logger.warning(f"⚠️ 導航失敗，當前 URL: {current_url}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ 導航到市場失敗: {e}")
            return False
    
    async def wait_for_element(self, selector: str, timeout: int = 10000):
        """等待元素出現"""
        try:
            return await self.page.wait_for_selector(selector, timeout=timeout)
        except Exception as e:
            self.logger.warning(f"⚠️ 等待元素失敗 {selector}: {e}")
            return None
    
    async def _setup_page_interceptors(self):
        """設置頁面攔截器"""
        async def handle_response(response):
            # 記錄重要的 API 響應
            if 'api' in response.url or 'ajax' in response.url:
                self.logger.debug(f"API 響應: {response.url} - {response.status}")
        
        self.context.on('response', handle_response)
    
    def _get_browser_args(self) -> list:
        """獲取瀏覽器啟動參數"""
        return [
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage',
            '--disable-web-security',
            '--disable-features=VizDisplayCompositor',
            '--no-sandbox',
            '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
            '--disable-renderer-backgrounding',
        ]
```

### 3. 市場分析器

```python
# dfautotrans/core/market_analyzer.py
import asyncio
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

from ..data.models import MarketItem, PriceHistory
from ..data.repositories import MarketDataRepository
from ..utils.logger import get_logger

@dataclass
class MarketOpportunity:
    """市場機會數據類"""
    item: MarketItem
    expected_profit: float
    profit_margin: float
    confidence_score: float
    recommended_quantity: int

@dataclass
class MarketAnalysis:
    """市場分析結果"""
    timestamp: datetime
    opportunities: List[MarketOpportunity]
    market_trends: Dict[str, float]
    has_opportunities: bool
    risk_level: str

class MarketAnalyzer:
    """市場分析引擎"""
    
    def __init__(self, config):
        self.config = config
        self.logger = get_logger(__name__)
        self.data_repo = MarketDataRepository()
        self.price_history: Dict[str, List[PriceHistory]] = {}
    
    async def analyze_market(self) -> MarketAnalysis:
        """執行完整的市場分析"""
        self.logger.info("📊 開始市場分析...")
        
        try:
            # 1. 搜索目標商品
            target_items = await self._search_target_items()
            
            # 2. 價格分析
            opportunities = []
            for item in target_items:
                opportunity = await self._analyze_item_opportunity(item)
                if opportunity and opportunity.confidence_score > self.config.min_confidence:
                    opportunities.append(opportunity)
            
            # 3. 市場趨勢分析
            market_trends = await self._analyze_market_trends()
            
            # 4. 綜合評估
            analysis = MarketAnalysis(
                timestamp=datetime.now(),
                opportunities=sorted(opportunities, key=lambda x: x.expected_profit, reverse=True),
                market_trends=market_trends,
                has_opportunities=len(opportunities) > 0,
                risk_level=self._calculate_risk_level(opportunities, market_trends)
            )
            
            self.logger.info(f"📈 市場分析完成，找到 {len(opportunities)} 個機會")
            return analysis
            
        except Exception as e:
            self.logger.error(f"❌ 市場分析失敗: {e}")
            raise
    
    async def _search_target_items(self) -> List[MarketItem]:
        """搜索目標商品"""
        # 實現搜索邏輯，類似於 JavaScript 版本的 searchItem 函數
        pass
    
    async def _analyze_item_opportunity(self, item: MarketItem) -> Optional[MarketOpportunity]:
        """分析單個商品的投資機會"""
        # 計算歷史平均價格
        avg_price = await self._get_historical_average_price(item.name)
        if not avg_price:
            return None
        
        # 計算預期利潤
        unit_price = item.price / item.quantity
        expected_profit = (avg_price * 0.9 - unit_price) * item.quantity  # 90% 的歷史均價作為賣價
        profit_margin = expected_profit / item.price if item.price > 0 else 0
        
        # 信心度評分（基於價格穩定性、交易量等）
        confidence_score = await self._calculate_confidence_score(item, avg_price)
        
        if profit_margin > self.config.min_profit_margin:
            return MarketOpportunity(
                item=item,
                expected_profit=expected_profit,
                profit_margin=profit_margin,
                confidence_score=confidence_score,
                recommended_quantity=item.quantity
            )
        
        return None
```

### 4. 交易執行器

```python
# dfautotrans/core/trade_executor.py
import asyncio
from typing import List, Optional, Dict
from dataclasses import dataclass
from datetime import datetime

from ..automation.human_behavior import HumanBehaviorSimulator
from ..automation.action_performer import ActionPerformer
from ..data.models import MarketItem, Transaction
from ..utils.logger import get_logger

@dataclass
class TradeResult:
    """交易結果"""
    success: bool
    transaction: Optional[Transaction]
    error_message: Optional[str]
    execution_time: float

class TradeExecutor:
    """交易執行引擎"""
    
    def __init__(self, config):
        self.config = config
        self.logger = get_logger(__name__)
        self.human_behavior = HumanBehaviorSimulator(config.human_behavior)
        self.action_performer = ActionPerformer()
        self.active_trades: List[Transaction] = []
    
    async def execute_buy_order(self, item: MarketItem) -> TradeResult:
        """執行購買訂單"""
        start_time = datetime.now()
        self.logger.info(f"🛒 開始購買: {item.name} - 價格: ${item.price}")
        
        try:
            # 1. 人性化行為模擬
            await self.human_behavior.simulate_pre_action_behavior()
            
            # 2. 點擊商品
            await self.action_performer.click_item(item.element_selector)
            await self.human_behavior.random_delay(500, 1000)
            
            # 3. 點擊購買按鈕
            buy_button = await self.action_performer.find_buy_button()
            if not buy_button:
                return TradeResult(False, None, "找不到購買按鈕", 0)
            
            await self.action_performer.human_click(buy_button)
            await self.human_behavior.random_delay(1000, 2000)
            
            # 4. 處理確認對話框
            confirm_success = await self._handle_purchase_confirmation()
            if not confirm_success:
                return TradeResult(False, None, "確認對話框處理失敗", 0)
            
            # 5. 驗證購買成功
            success = await self._verify_purchase_success(item)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            if success:
                transaction = Transaction(
                    type="BUY",
                    item_name=item.name,
                    quantity=item.quantity,
                    price=item.price,
                    timestamp=datetime.now()
                )
                
                self.logger.info(f"✅ 購買成功: {item.name}")
                return TradeResult(True, transaction, None, execution_time)
            else:
                return TradeResult(False, None, "購買驗證失敗", execution_time)
                
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self.logger.error(f"❌ 購買失敗: {e}")
            return TradeResult(False, None, str(e), execution_time)
    
    async def execute_sell_order(self, item: MarketItem, sell_price: float) -> TradeResult:
        """執行銷售訂單"""
        start_time = datetime.now()
        self.logger.info(f"🏷️ 開始銷售: {item.name} - 價格: ${sell_price}")
        
        try:
            # 1. 人性化行為模擬
            await self.human_behavior.simulate_pre_action_behavior()
            
            # 2. 右鍵點擊庫存商品
            await self.action_performer.right_click_item(item.element_selector)
            await self.human_behavior.random_delay(800, 1500)
            
            # 3. 點擊 Sell 選項
            sell_option = await self.action_performer.find_sell_option()
            if not sell_option:
                return TradeResult(False, None, "找不到銷售選項", 0)
            
            await self.action_performer.human_click(sell_option)
            await self.human_behavior.random_delay(1000, 2000)
            
            # 4. 輸入價格
            price_input = await self.action_performer.find_price_input()
            if not price_input:
                return TradeResult(False, None, "找不到價格輸入欄", 0)
            
            await self.action_performer.human_type(price_input, str(sell_price))
            await self.human_behavior.random_delay(500, 1000)
            
            # 5. 確認銷售
            confirm_success = await self._handle_sell_confirmation()
            if not confirm_success:
                return TradeResult(False, None, "銷售確認失敗", 0)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            transaction = Transaction(
                type="SELL",
                item_name=item.name,
                quantity=item.quantity,
                price=sell_price,
                timestamp=datetime.now()
            )
            
            self.logger.info(f"✅ 銷售成功: {item.name}")
            return TradeResult(True, transaction, None, execution_time)
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self.logger.error(f"❌ 銷售失敗: {e}")
            return TradeResult(False, None, str(e), execution_time)
```

## 🛡️ 反檢測系統

### 高級反檢測管理器

```python
# dfautotrans/automation/anti_detection.py
import random
import asyncio
from typing import Dict, Any, List
from playwright.async_api import Page

class AntiDetectionManager:
    """高級反檢測系統"""
    
    def __init__(self, config):
        self.config = config
        self.session_fingerprint = self._generate_fingerprint()
        self.behavior_patterns = self._load_behavior_patterns()
    
    async def get_context_config(self) -> Dict[str, Any]:
        """獲取瀏覽器上下文配置"""
        return {
            'viewport': self._random_viewport(),
            'user_agent': self._random_user_agent(),
            'locale': 'en-US',
            'timezone_id': 'America/New_York',
            'geolocation': {'latitude': 40.7128, 'longitude': -74.0060},
            'permissions': ['geolocation'],
            'extra_http_headers': self._get_random_headers(),
            'device_scale_factor': random.choice([1, 1.25, 1.5, 2]),
        }
    
    async def inject_scripts(self, page: Page):
        """注入反檢測腳本"""
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            
            // 重寫 plugins 屬性
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            
            // 隱藏自動化特徵
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
        """)
```

## 📊 數據層設計

### 數據模型

```python
# dfautotrans/data/models.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
from enum import Enum

class TransactionType(Enum):
    BUY = "BUY"
    SELL = "SELL"

@dataclass
class MarketItem:
    """市場商品模型"""
    name: str
    price: float
    quantity: int
    seller: str
    element_selector: str
    timestamp: datetime
    
    @property
    def unit_price(self) -> float:
        return self.price / self.quantity if self.quantity > 0 else 0

@dataclass
class Transaction:
    """交易記錄模型"""
    id: Optional[int] = None
    type: TransactionType = TransactionType.BUY
    item_name: str = ""
    quantity: int = 0
    price: float = 0.0
    timestamp: datetime = datetime.now()
    success: bool = True
    error_message: Optional[str] = None

@dataclass
class InventoryItem:
    """庫存物品模型"""
    name: str
    quantity: int
    estimated_value: float
    last_updated: datetime
    sell_priority: int  # 銷售優先級

@dataclass
class PriceHistory:
    """價格歷史模型"""
    item_name: str
    price: float
    quantity: int
    timestamp: datetime
    source: str  # market, inventory, etc.
```

## ⚙️ 配置系統

```python
# dfautotrans/config/settings.py
from pydantic import BaseSettings, Field
from typing import Dict, List, Optional

class BrowserConfig(BaseSettings):
    """瀏覽器配置"""
    headless: bool = False
    slow_mo: int = 100
    timeout: int = 30000
    viewport_width: int = 1920
    viewport_height: int = 1080

class TradingConfig(BaseSettings):
    """交易配置"""
    target_items: List[str] = ["12.7mm Rifle Bullets"]
    max_price_per_unit: float = 11.6
    sell_price_multiplier: float = 1.01
    max_investment: float = 1000000
    min_profit_margin: float = 0.15
    max_daily_trades: int = 100

class RiskConfig(BaseSettings):
    """風險管理配置"""
    stop_loss_percentage: float = 0.2
    max_items_per_type: int = 10
    diversification_threshold: float = 0.3
    emergency_stop_enabled: bool = True

class AntiDetectionConfig(BaseSettings):
    """反檢測配置"""
    mouse_movement_variation: float = 0.3
    typing_delay_min: int = 50
    typing_delay_max: int = 150
    action_delay_min: int = 300
    action_delay_max: int = 800
    random_pause_probability: float = 0.1

class Settings(BaseSettings):
    """主配置類"""
    browser: BrowserConfig = BrowserConfig()
    trading: TradingConfig = TradingConfig()
    risk: RiskConfig = RiskConfig()
    anti_detection: AntiDetectionConfig = AntiDetectionConfig()
    
    # 數據庫
    database_url: str = "sqlite:///dfautotrans.db"
    
    # 日誌
    log_level: str = "INFO"
    log_file: str = "dfautotrans.log"
    
    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'
```

## 🚀 主程序入口

```python
# main.py
import asyncio
import argparse

from dfautotrans.app import DeadFrontierAutoTrader
from dfautotrans.config.settings import Settings
from dfautotrans.utils.logger import setup_logging

async def main():
    """主程序入口"""
    parser = argparse.ArgumentParser(description="Dead Frontier Auto Trader")
    parser.add_argument("--config", type=str, help="配置文件路徑")
    parser.add_argument("--headless", action="store_true", help="無頭模式")
    parser.add_argument("--dry-run", action="store_true", help="測試模式")
    
    args = parser.parse_args()
    
    # 加載配置
    config = Settings()
    if args.headless:
        config.browser.headless = True
    
    # 設置日誌
    setup_logging(config.log_level, config.log_file)
    
    # 啟動交易系統
    trader = DeadFrontierAutoTrader(config)
    await trader.start()

if __name__ == "__main__":
    asyncio.run(main())
```

## 📦 依賴管理

```python
# requirements.txt
playwright>=1.40.0
pydantic>=2.0.0
sqlalchemy>=2.0.0
alembic>=1.12.0
loguru>=0.7.0
python-dotenv>=1.0.0
```

這個架構提供了：

✅ **完整的模塊化設計**
✅ **強大的反檢測能力**  
✅ **靈活的配置系統**
✅ **完善的錯誤處理**
✅ **數據持久化和分析**
✅ **基礎日誌系統**
✅ **易於擴展和維護**

你希望我開始實現哪個核心模組？ 