# Dead Frontier 自動交易系統 - 交易流程文檔

## URL 路由系統

### 主要頁面URL
1. **登錄頁** (會彈出登錄對話框)
   ```
   https://www.deadfrontier.com/index.php?autologin=1
   ```

2. **首頁**
   ```
   https://fairview.deadfrontier.com/onlinezombiemmo/index.php
   ```

3. **市場頁面** (同時可見inventory)
   ```
   https://fairview.deadfrontier.com/onlinezombiemmo/index.php?page=35
   ```

4. **銀行頁面** (上架貨品賣出後錢會存入Bank)
   ```
   https://fairview.deadfrontier.com/onlinezombiemmo/index.php?page=15
   ```

5. **倉庫頁面** (同時可見inventory)
   ```
   https://fairview.deadfrontier.com/onlinezombiemmo/index.php?page=50
   ```

## 交易系統邏輯流程

### 1. 登錄檢查階段
- 檢查當前登錄狀態
- 如果未登錄，自動執行登錄流程
- 登錄後會自動進入首頁

### 2. 資源檢查階段
- 檢查角色身上的錢數
- 在配置文件中設置最低資金界線
- 低於界線時暫停交易系統

### 3. 空間管理階段
- 進入Marketplace檢查inventory空間
- 如果inventory沒有空間：
  - 前往Storage頁面
  - 使用"存入所有inventory"按鈕一鍵存入Storage
- 如果Storage和inventory都沒有空間：
  - 暫停交易系統，等待空間釋放

### 4. 購買決策階段
- 根據交易貨品清單和交易策略
- 掃描市場尋找值得購買的目標貨品
- 執行購買操作

### 5. 銷售管理階段
- 當沒有值得購買的貨品時
- 或余額低於設定界線時
- 前往selling section上架inventory中的貨品

### 6. 上架限制管理
- 系統限制：最多可上架30個貨品
- 頁面顯示格式：例如 "6/30"
- 當上架數達到限制且沒有值得購買的貨品時：
  - 暫停交易系統
  - 等待市場更新（貨品被購買後會釋放貨架空間）

### 7. 等待策略
#### 情況A：完全阻塞狀態
- 條件：角色身上沒錢 + bank沒錢 + inventory/storage/貨架都沒空間
- 動作：等待市場刷新（貨品賣掉可釋放空間並在bank獲得收入）

#### 情況B：正常等待狀態
- 條件：不符合情況A的其他狀況
- 當沒有值得購買的貨品時
- 動作：等待市場更新（每次等待1分鐘）

## 關鍵業務規則

### 資金管理
- 設置最低資金界線，低於此值不執行交易
- 身上沒錢時自動前往bank取出全部資金

### 空間管理
- inventory空間不足時自動存入Storage
- Storage + inventory + 貨架空間全滿時暫停系統

### 市場更新機制
- 正常情況：每分鐘檢查一次市場
- 完全阻塞情況：等待貨品賣出釋放空間和資金

### 上架限制
- 系統最大上架數：30個貨品
- 達到限制時優先等待貨品賣出釋放空間

## 頁面導航規則
- 登錄後不需要點擊首頁按鈕
- 直接通過URL訪問各個功能頁面
- 每個頁面都能檢查角色當前資金狀況 