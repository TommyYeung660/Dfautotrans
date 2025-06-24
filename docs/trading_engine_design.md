# Dead Frontier 自動交易引擎 - 系統設計文檔

## 系統架構概述

### 核心模組架構
```
dfautotrans/
├── core/                    # 核心業務邏輯
│   ├── trading_engine.py    # 主交易引擎
│   ├── state_machine.py     # 狀態機管理
│   └── page_navigator.py    # 頁面導航器
├── automation/              # 自動化操作
│   ├── browser_manager.py   # 瀏覽器管理
│   ├── login_handler.py     # 登錄處理
│   ├── market_operations.py # 市場操作
│   ├── inventory_manager.py # 庫存管理
│   └── bank_operations.py   # 銀行操作
├── strategies/              # 交易策略
│   ├── buying_strategy.py   # 購買策略
│   └── selling_strategy.py  # 銷售策略
└── data/                    # 數據管理
    ├── models.py           # 數據模型
    └── state_persistence.py # 狀態持久化
```

## 核心交易引擎 (TradingEngine)

### 主要職責
1. 協調各個子系統的運作
2. 執行完整的交易週期
3. 監控系統狀態和錯誤處理
4. 決策何時暫停或繼續交易

### 交易週期流程
```python
class TradingCycle(Enum):
    LOGIN_CHECK = "login_check"
    RESOURCE_CHECK = "resource_check"
    SPACE_MANAGEMENT = "space_management"
    MARKET_ANALYSIS = "market_analysis"
    BUYING_PHASE = "buying_phase"
    SELLING_PHASE = "selling_phase"
    WAIT_PHASE = "wait_phase"
    ERROR_HANDLING = "error_handling"
```

## 狀態機管理 (StateMachine)

### 系統狀態定義
```python
class TradingState(Enum):
    # 基礎狀態
    IDLE = "idle"
    INITIALIZING = "initializing"
    
    # 登錄狀態
    LOGIN_REQUIRED = "login_required"
    LOGGING_IN = "logging_in"
    LOGIN_FAILED = "login_failed"
    
    # 資源檢查狀態
    CHECKING_RESOURCES = "checking_resources"
    INSUFFICIENT_FUNDS = "insufficient_funds"
    WITHDRAWING_FROM_BANK = "withdrawing_from_bank"
    
    # 空間管理狀態
    CHECKING_INVENTORY = "checking_inventory"
    DEPOSITING_TO_STORAGE = "depositing_to_storage"
    SPACE_FULL = "space_full"
    
    # 交易狀態
    MARKET_SCANNING = "market_scanning"
    BUYING = "buying"
    SELLING = "selling"
    
    # 等待狀態
    WAITING_NORMAL = "waiting_normal"
    WAITING_BLOCKED = "waiting_blocked"
    
    # 錯誤狀態
    ERROR = "error"
    CRITICAL_ERROR = "critical_error"
```

### 状態轉換規則
- **LOGIN_REQUIRED** → **LOGGING_IN** → **CHECKING_RESOURCES**
- **INSUFFICIENT_FUNDS** → **WITHDRAWING_FROM_BANK** → **CHECKING_RESOURCES**
- **CHECKING_INVENTORY** → **DEPOSITING_TO_STORAGE** → **MARKET_SCANNING**
- **MARKET_SCANNING** → **BUYING** or **SELLING** or **WAITING_NORMAL**
- **SPACE_FULL** → **WAITING_BLOCKED**

## 頁面導航器 (PageNavigator)

### 核心功能
```python
class PageNavigator:
    async def ensure_logged_in(self) -> bool
    async def navigate_to_home(self) -> bool
    async def navigate_to_marketplace(self) -> bool
    async def navigate_to_bank(self) -> bool
    async def navigate_to_storage(self) -> bool
    async def get_current_cash(self) -> int
    async def check_login_status(self) -> bool
```

### URL管理
- 所有頁面通過直接URL訪問，無需點擊導航按鈕
- 每個頁面都能獲取角色當前資金狀況
- 自動處理頁面加載和狀態檢查

## 市場操作模組 (MarketOperations)

### 購買流程
```python
class MarketOperations:
    async def scan_market_items(self) -> List[MarketItem]
    async def evaluate_purchase_opportunities(self, items: List[MarketItem]) -> List[PurchaseOpportunity]
    async def execute_purchase(self, opportunity: PurchaseOpportunity) -> bool
    async def check_inventory_space(self) -> InventoryStatus
```

### 銷售流程
```python
    async def get_selling_slots_status(self) -> SellingSlotsStatus  # 例如: 6/30
    async def list_inventory_items(self) -> List[InventoryItem]
    async def calculate_selling_price(self, item: InventoryItem) -> float
    async def list_item_for_sale(self, item: InventoryItem, price: float) -> bool
```

## 庫存管理模組 (InventoryManager)

### 空間管理策略
```python
class InventoryManager:
    async def check_inventory_full(self) -> bool
    async def check_storage_space(self) -> StorageStatus
    async def deposit_all_to_storage(self) -> bool
    async def get_inventory_items(self) -> List[InventoryItem]
    async def calculate_space_requirements(self, items: List[MarketItem]) -> int
```

### 智能空間分配
- 優先保留高價值物品在inventory
- 自動將低價值物品存入storage
- 預測購買需求並預留空間

## 銀行操作模組 (BankOperations)

### 資金管理
```python
class BankOperations:
    async def get_bank_balance(self) -> int
    async def withdraw_all_funds(self) -> bool
    async def check_total_available_funds(self) -> int  # 身上 + 銀行
    async def ensure_minimum_funds(self, required: int) -> bool
```

## 交易策略模組

### 購買策略 (BuyingStrategy)
```python
class BuyingStrategy:
    def evaluate_item(self, item: MarketItem) -> PurchaseDecision
    def calculate_profit_potential(self, item: MarketItem) -> float
    def check_market_conditions(self) -> MarketCondition
    def prioritize_purchases(self, opportunities: List[PurchaseOpportunity]) -> List[PurchaseOpportunity]
```

### 銷售策略 (SellingStrategy)
```python
class SellingStrategy:
    def determine_selling_price(self, item: InventoryItem) -> float
    def select_items_to_sell(self, items: List[InventoryItem]) -> List[InventoryItem]
    def optimize_selling_slots(self, available_slots: int) -> List[SellOrder]
```

## 等待和重試機制

### 等待策略
```python
class WaitStrategy:
    NORMAL_WAIT = 60      # 正常市場等待 1分鐘
    BLOCKED_WAIT = 300    # 完全阻塞等待 5分鐘
    LOGIN_RETRY_WAIT = 30 # 登錄重試等待 30秒
```

### 阻塞狀態判斷
- **完全阻塞**: 沒錢 + 沒bank錢 + 沒inventory/storage/貨架空間
- **正常等待**: 沒有值得購買的貨品但系統正常運作

## 錯誤處理和恢復

### 錯誤分類
1. **可恢復錯誤**: 網絡超時、頁面加載失敗
2. **狀態錯誤**: 登錄失效、頁面結構變化
3. **業務錯誤**: 餘額不足、空間不足
4. **嚴重錯誤**: 系統異常、配置錯誤

### 恢復策略
- 自動重試機制 (最多3次)
- 狀態回滾和重新初始化
- 錯誤日誌記錄和報告
- 緊急停止機制

## 性能優化

### 並發處理
- 市場掃描和價格分析並行處理
- 批量操作減少頁面跳轉
- 智能緩存減少重複查詢

### 資源管理
- 連接池管理
- 內存使用優化
- 日誌文件輪轉

## 監控和日誌

### 關鍵指標監控
- 交易成功率
- 平均利潤率
- 系統運行時間
- 錯誤發生率

### 日誌記錄
- 交易操作日誌
- 系統狀態變化日誌
- 錯誤和異常日誌
- 性能指標日誌 