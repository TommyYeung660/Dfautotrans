# Dead Frontier 自動交易系統開發文檔

## 項目概述

基於現有的 `marketplace_helper.js`，開發一個全自動的商品交易系統，能夠：
- 自動尋找並購買低價商品
- 自動管理庫存
- 自動上架銷售商品
- 自動進行銀行操作

## 1. 網頁結構分析

### 1.1 已知DOM元素（基於現有代碼）

#### 市場相關元素：
- `#itemDisplay` - 商品顯示區域
- `.fakeItem` - 商品項目（含 `dataset.price` 和 `dataset.quantity`）
- `.salePrice` - 價格顯示
- `#loadBuying` - 購買標籤頁
- `#searchField` - 搜索欄
- `#makeSearch` - 搜索按鈕
- `#invController` - 庫存控制器
- `#infoBox > .itemName` - 商品名稱
- `[data-action="buyItem"]` - 購買按鈕

#### 需要進一步分析的元素：
- 庫存界面元素
- 銀行界面元素
- 上架銷售界面元素
- 現金餘額顯示
- 庫存容量顯示

### 1.2 需要爬取的額外元素

```javascript
// 需要識別的關鍵元素
const ELEMENTS = {
    // 庫存相關
    inventoryItems: '.item', // 庫存商品
    inventoryFull: '', // 庫存滿的指示器
    
    // 財務相關
    cashBalance: '', // 現金餘額
    bankBalance: '', // 銀行餘額
    
    // 銷售相關
    sellTab: '', // 銷售標籤
    sellButton: '', // 上架按鈕
    priceInput: '', // 價格輸入欄
    
    // 銀行相關
    bankTab: '', // 銀行標籤
    depositButton: '', // 存款按鈕
    depositInput: '', // 存款金額輸入
};
```

## 2. 核心功能模組設計

### 2.1 市場分析模組 (MarketAnalyzer)

```javascript
class MarketAnalyzer {
    constructor() {
        this.priceHistory = new Map(); // 商品價格歷史
        this.marketData = new Map(); // 市場數據
    }
    
    // 獲取所有商品資訊
    async getAllItems() {
        // 實現商品數據爬取
    }
    
    // 分析價格趨勢
    analyzePriceTrends(itemName) {
        // 實現價格分析邏輯
    }
    
    // 判斷是否為好價格
    isGoodDeal(item, currentPrice) {
        // 實現價格判斷邏輯
    }
    
    // 獲取市場平均價
    getMarketPrice(itemName) {
        // 實現市場價格獲取
    }
}
```

### 2.2 庫存管理模組 (InventoryManager)

```javascript
class InventoryManager {
    constructor() {
        this.inventory = [];
        this.maxCapacity = 0;
    }
    
    // 檢查庫存狀態
    checkInventoryStatus() {
        // 實現庫存檢查
    }
    
    // 獲取庫存空間
    getAvailableSpace() {
        // 實現空間計算
    }
    
    // 獲取庫存商品列表
    getInventoryItems() {
        // 實現庫存商品獲取
    }
    
    // 選擇要銷售的商品
    selectItemsToSell() {
        // 實現銷售商品選擇邏輯
    }
}
```

### 2.3 交易執行模組 (TradeExecutor)

```javascript
class TradeExecutor {
    constructor() {
        this.isTrading = false;
        this.tradeQueue = [];
    }
    
    // 執行購買操作
    async buyItem(item) {
        // 實現購買邏輯
        // 1. 點擊商品
        // 2. 確認購買
        // 3. 等待交易完成
    }
    
    // 執行銷售操作
    async sellItem(item, price) {
        // 實現銷售邏輯
        // 1. 選擇商品
        // 2. 設定價格
        // 3. 上架銷售
    }
    
    // 銀行操作
    async bankOperation(action, amount) {
        // 實現銀行存取款
    }
}
```

### 2.4 風險管理模組 (RiskManager)

```javascript
class RiskManager {
    constructor() {
        this.maxInvestment = 1000000; // 最大投資額
        this.profitMargin = 0.1; // 最小利潤率
        this.maxItemsPerCategory = 5; // 每類商品最大持有量
    }
    
    // 檢查交易風險
    assessRisk(item, price) {
        // 實現風險評估
    }
    
    // 檢查投資限額
    checkInvestmentLimit(amount) {
        // 實現投資限額檢查
    }
    
    // 多樣化檢查
    checkDiversification(itemCategory) {
        // 實現投資多樣化檢查
    }
}
```

## 3. 業務流程設計

### 3.1 主要業務流程

```javascript
class AutoTrader {
    constructor() {
        this.analyzer = new MarketAnalyzer();
        this.inventory = new InventoryManager();
        this.executor = new TradeExecutor();
        this.riskManager = new RiskManager();
        this.isRunning = false;
    }
    
    // 主要運行循環
    async run() {
        while (this.isRunning) {
            try {
                // 1. 檢查庫存狀態
                await this.checkInventoryStatus();
                
                // 2. 如果庫存滿了，執行銷售
                if (this.inventory.isFull()) {
                    await this.sellItems();
                }
                
                // 3. 尋找購買機會
                await this.findBuyingOpportunities();
                
                // 4. 執行銀行操作
                await this.manageBankAccount();
                
                // 5. 等待下一輪
                await this.sleep(5000); // 5秒間隔
                
            } catch (error) {
                console.error('交易錯誤:', error);
                await this.sleep(10000); // 錯誤後等待10秒
            }
        }
    }
}
```

### 3.2 詳細業務邏輯

#### 3.2.1 購買邏輯流程
```
1. 搜索所有商品類別
2. 獲取商品列表和價格
3. 與歷史價格比較
4. 計算潛在利潤
5. 風險評估
6. 執行購買決策
7. 更新數據記錄
```

#### 3.2.2 銷售邏輯流程
```
1. 檢查庫存商品
2. 獲取市場當前價格
3. 計算合適的銷售價格
4. 上架商品
5. 監控銷售狀態
6. 更新庫存記錄
```

#### 3.2.3 銀行管理流程
```
1. 檢查現金餘額
2. 計算需要的交易資金
3. 自動存取款操作
4. 維持最佳現金流
```

## 4. 技術實現要點

### 4.1 DOM操作和事件處理

```javascript
// 安全的DOM操作
function safeClick(element) {
    return new Promise((resolve) => {
        if (element && typeof element.click === 'function') {
            element.click();
            setTimeout(resolve, 1000); // 等待響應
        } else {
            resolve();
        }
    });
}

// 等待元素出現
function waitForElement(selector, timeout = 10000) {
    return new Promise((resolve, reject) => {
        const element = document.querySelector(selector);
        if (element) {
            resolve(element);
            return;
        }
        
        const observer = new MutationObserver(() => {
            const element = document.querySelector(selector);
            if (element) {
                observer.disconnect();
                resolve(element);
            }
        });
        
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
        
        setTimeout(() => {
            observer.disconnect();
            reject(new Error('元素未找到: ' + selector));
        }, timeout);
    });
}
```

### 4.2 數據持久化

```javascript
// 使用 localStorage 存儲數據
class DataStorage {
    static save(key, data) {
        localStorage.setItem(`autotrader_${key}`, JSON.stringify(data));
    }
    
    static load(key, defaultValue = null) {
        const data = localStorage.getItem(`autotrader_${key}`);
        return data ? JSON.parse(data) : defaultValue;
    }
    
    static savePriceHistory(itemName, price) {
        const history = this.load('priceHistory', {});
        if (!history[itemName]) {
            history[itemName] = [];
        }
        history[itemName].push({
            price: price,
            timestamp: Date.now()
        });
        
        // 只保留最近100筆記錄
        if (history[itemName].length > 100) {
            history[itemName] = history[itemName].slice(-100);
        }
        
        this.save('priceHistory', history);
    }
}
```

### 4.3 錯誤處理和重試機制

```javascript
class RetryHandler {
    static async retry(fn, maxRetries = 3, delay = 1000) {
        for (let i = 0; i < maxRetries; i++) {
            try {
                return await fn();
            } catch (error) {
                console.log(`嘗試 ${i + 1}/${maxRetries} 失敗:`, error);
                if (i === maxRetries - 1) throw error;
                await new Promise(resolve => setTimeout(resolve, delay * (i + 1)));
            }
        }
    }
}
```

## 5. 配置系統

### 5.1 用戶配置選項

```javascript
const CONFIG = {
    // 交易參數
    trading: {
        maxInvestment: 1000000,     // 最大投資金額
        minProfitMargin: 0.15,      // 最小利潤率 15%
        maxItemsPerType: 10,        // 每類商品最大持有量
        tradeInterval: 5000,        // 交易間隔(毫秒)
    },
    
    // 風險控制
    risk: {
        stopLossPercentage: 0.2,    // 止損百分比
        maxDailyTrades: 100,        // 每日最大交易次數
        emergencyStopEnabled: true,  // 緊急停止開關
    },
    
    // 銀行管理
    banking: {
        minCashReserve: 50000,      // 最小現金儲備
        autoDepositThreshold: 500000, // 自動存款閾值
        maxCashHolding: 200000,     // 最大現金持有量
    },
    
    // 日誌設定
    logging: {
        enableDebug: true,          // 啟用調試日誌
        logTradeHistory: true,      // 記錄交易歷史
        maxLogEntries: 1000,        // 最大日誌條目
    }
};
```

## 6. 開發階段計劃

### 第一階段：基礎框架 (1-2 週)
- [ ] 完成DOM元素分析和映射
- [ ] 建立基礎類結構
- [ ] 實現安全的DOM操作函數
- [ ] 建立配置系統

### 第二階段：核心功能 (2-3 週)
- [ ] 實現市場數據爬取
- [ ] 完成庫存管理功能
- [ ] 實現基本購買/銷售邏輯
- [ ] 建立價格分析算法

### 第三階段：自動化邏輯 (2-3 週)
- [ ] 完成自動交易主循環
- [ ] 實現風險管理系統
- [ ] 加入銀行自動化操作
- [ ] 完善錯誤處理機制

### 第四階段：優化測試 (1-2 週)
- [ ] 性能優化
- [ ] 安全性測試
- [ ] 用戶介面優化
- [ ] 文檔完善

## 7. 安全考慮

### 7.1 反檢測措施
- 隨機化操作間隔
- 模擬人類操作模式
- 避免過於頻繁的操作
- 加入錯誤和延遲模擬

### 7.2 緊急停止機制
- 檢測異常市場狀況
- 損失限制觸發停止
- 手動緊急停止按鈕
- 自動備份重要數據

## 8. 監控和日誌

### 8.1 實時監控面板
```javascript
class MonitoringPanel {
    constructor() {
        this.createPanel();
    }
    
    createPanel() {
        // 創建浮動監控面板
        // 顯示當前狀態、利潤、交易次數等
    }
    
    updateStats() {
        // 更新統計數據
    }
}
```

### 8.2 詳細日誌記錄
- 所有交易記錄
- 錯誤和異常日誌
- 性能指標記錄
- 市場數據變化記錄

## 9. 部署和維護

### 9.1 Tampermonkey 腳本配置
```javascript
// ==UserScript==
// @name         Dead Frontier Auto Trader
// @namespace    http://tampermonkey.net/
// @version      1.0000
// @description  Automated trading system for Dead Frontier
// @author       your_name
// @match        https://fairview.deadfrontier.com/onlinezombiemmo/index.php*
// @grant        none
// @run-at       document-idle
// ==/UserScript==
```

### 9.2 版本控制和更新
- 版本號管理
- 自動更新檢查
- 配置遷移機制
- 向後兼容性

## 10. 測試策略

### 10.1 單元測試
- 每個模組的獨立測試
- 模擬市場環境測試
- 邊界條件測試

### 10.2 集成測試
- 完整流程測試
- 異常情況處理測試
- 長時間運行穩定性測試

### 10.3 風險測試
- 小額資金測試
- 模擬市場波動測試
- 緊急停止機制測試

這個開發文檔提供了一個完整的框架來實現您的自動交易系統。建議從第一階段開始，逐步實現每個功能模組。 