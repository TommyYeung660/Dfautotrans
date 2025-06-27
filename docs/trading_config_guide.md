# Dead Frontier 自動交易系統配置指南

## 配置文件說明

本文檔詳細說明 `trading_config.json` 中每個配置項的作用、建議值和使用場景。

---

## 1. 市場搜索配置 (market_search)

### target_items
- **說明**：目標物品清單，系統會精確匹配這些物品名稱進行購買
- **類型**：字符串數組
- **預設值**：`["12.7mm Rifle Bullets", "14mm Rifle Bullets", "9mm Rifle Bullets", "10 Gauge Shells", "12 Gauge Shells", "Energy Cell", "Gasoline"]`
- **建議**：
  - 使用完整且精確的物品名稱
  - 系統只會購買完全匹配的物品，避免誤買
  - 可根據市場需求調整目標物品

### max_price_per_unit
- **說明**：每種目標物品的最大購買價格，與 target_items 數組一一對應
- **類型**：浮點數數組
- **預設值**：`[11.0, 13.0, 11.0, 15.0, 16.0, 15.0, 3.0]`
- **對應關係**：
  - `12.7mm Rifle Bullets`: $11.0
  - `14mm Rifle Bullets`: $13.0
  - `9mm Rifle Bullets`: $11.0
  - `10 Gauge Shells`: $15.0
  - `12 Gauge Shells`: $16.0
  - `Energy Cell`: $15.0
  - `Gasoline`: $3.0
- **建議**：
  - 根據每種物品的市場價格和利潤空間設定
  - 數組長度必須與 target_items 相同
  - 定期根據市場變化調整價格

### max_items_per_search
- **說明**：每次搜索最多掃描的物品數量
- **類型**：整數
- **預設值**：`13`
- **建議**：
  - 10-100：平衡搜索全面性與速度
  - 數值越大掃描越全面但耗時更長
  - 網路較慢時建議降低此值

### search_timeout_seconds
- **說明**：搜索操作的超時時間（秒）
- **類型**：整數
- **預設值**：`15`
- **建議**：10-60秒，防止搜索卡住

### max_total_investment
- **說明**：單次交易週期的最大總投資額度
- **類型**：浮點數
- **預設值**：`100000.0`
- **建議**：根據可用資金的 60-80% 設定

### min_profit_margin
- **說明**：最小利潤率要求，低於此利潤率不會購買
- **類型**：浮點數 (0.15 = 15%)
- **預設值**：`0.15`
- **建議**：
  - 保守：15-20%
  - 積極：10-15%
  - 高風險：5-10%

### target_profit_margin
- **說明**：目標利潤率，系統會優先選擇達到此利潤率的物品
- **類型**：浮點數 (0.3 = 30%)
- **預設值**：`0.3`
- **建議**：
  - 通常設定為 min_profit_margin 的 1.5-2 倍
  - 市場穩定時可設高一些

### max_purchases_per_cycle
- **說明**：每個交易週期最多購買的物品數量
- **類型**：整數
- **預設值**：`10`
- **建議**：
  - 新手：3-5
  - 有經驗：5-10
  - 專家：10-15

### max_quantity_per_item
- **說明**：單個物品的最大購買數量
- **類型**：整數
- **預設值**：`1000`
- **建議**：根據庫存空間和資金限制調整

### max_high_risk_purchases
- **說明**：每週期最多允許的高風險購買數量
- **類型**：整數
- **預設值**：`3`
- **建議**：不超過總購買數量的 30-50%

### high_risk_price_threshold
- **說明**：高風險物品的價格門檻，超過此價格視為高風險
- **類型**：浮點數
- **預設值**：`5000.0`
- **建議**：根據個人風險承受能力調整

### max_same_item_purchases
- **說明**：同類物品的最大購買數量，避免過度集中投資
- **類型**：整數
- **預設值**：`5`
- **建議**：保持投資多樣化

### priority_items
- **說明**：物品購買優先級，數字越小優先級越高
- **類型**：物件
- **預設值**：
  ```json
  {
    "12.7mm Rifle Bullets": 1,
    "14mm Rifle Bullets": 2,
    "9mm Rifle Bullets": 3,
    "10 Gauge Shells": 4,
    "12 Gauge Shells": 5,
    "Energy Cell": 6,
    "Gasoline": 7
  }
  ```
- **建議**：根據市場需求和利潤率調整優先級

### price_analysis_samples
- **說明**：價格分析樣本數量，用於計算平均價格和趨勢
- **類型**：整數
- **預設值**：`20`
- **建議**：10-30，樣本越多分析越準確但耗時更長

---

## 2. 購買策略配置 (buying)

### max_total_investment
- **說明**：單次交易週期的最大總投資額度
- **類型**：浮點數
- **預設值**：`100000.0`
- **建議**：根據可用資金的 60-80% 設定

### diversification_enabled
- **說明**：是否啟用多樣化投資策略，避免過度集中投資單一物品類型
- **類型**：布林值
- **預設值**：`true`
- **建議**：建議保持啟用以降低風險

### priority_items
- **說明**：物品購買優先級，數字越小優先級越高
- **類型**：物件
- **預設值**：
  ```json
  {
    "12.7mm Rifle Bullets": 1,
    "14mm Rifle Bullets": 2,
    "9mm Rifle Bullets": 3,
    "10 Gauge Shells": 4,
    "12 Gauge Shells": 5,
    "Energy Cell": 6,
    "Gasoline": 7
  }
  ```
- **建議**：根據市場需求和利潤率調整優先級

### price_analysis_samples
- **說明**：價格分析樣本數量，用於計算平均價格和趨勢
- **類型**：整數
- **預設值**：`20`
- **建議**：10-30，樣本越多分析越準確但耗時更長

---

## 3. 銷售策略配置 (selling)

### markup_percentage
- **說明**：標準加價比例，購買價格基礎上的加價幅度
- **類型**：浮點數 (0.2 = 20%)
- **預設值**：`0.2`
- **建議**：
  - 快速周轉：15-25%
  - 穩定利潤：25-35%
  - 高利潤：35-50%

### min_markup_percentage
- **說明**：最小加價比例，保證基本利潤
- **類型**：浮點數 (0.1 = 10%)
- **預設值**：`0.1`
- **建議**：不低於 5%，確保覆蓋交易成本

### max_markup_percentage
- **說明**：最大加價比例，避免定價過高賣不出去
- **類型**：浮點數 (0.5 = 50%)
- **預設值**：`0.5`
- **建議**：根據物品稀有度和市場需求調整

### min_holding_time_hours
- **說明**：最短持有時間（小時），購買後至少持有多久才能賣出
- **類型**：整數
- **預設值**：`1`
- **建議**：避免過於頻繁的交易

### max_holding_time_hours
- **說明**：最長持有時間（小時），超過此時間會考慮降價銷售
- **類型**：整數
- **預設值**：`24`
- **建議**：12-48小時，根據物品周轉速度調整

### max_inventory_slots_used
- **說明**：最大庫存使用格數，超過此數量會優先清理庫存
- **類型**：整數
- **預設值**：`25`
- **建議**：根據總庫存空間的 50-80% 設定

### inventory_threshold_percentage
- **說明**：庫存使用率閾值，超過此比例會開始積極銷售
- **類型**：浮點數 (0.8 = 80%)
- **預設值**：`0.8`
- **建議**：70-90%

### max_selling_slots_used
- **說明**：最大銷售位使用數量，控制同時上架的物品數量
- **類型**：整數
- **預設值**：`25`
- **建議**：根據可用銷售位調整

### selling_slots_threshold_percentage
- **說明**：銷售位使用率閾值，超過此比例會暫停新上架
- **類型**：浮點數 (0.95 = 95%)
- **預設值**：`0.95`
- **建議**：80-95%

### price_adjustment_enabled
- **說明**：是否啟用動態價格調整
- **類型**：布林值
- **預設值**：`true`
- **建議**：建議開啟以提高銷售效率

### price_reduction_after_hours
- **說明**：多少小時後開始降價
- **類型**：整數
- **預設值**：`6`
- **建議**：4-12小時

### price_reduction_percentage
- **說明**：每次降價的幅度
- **類型**：浮點數 (0.05 = 5%)
- **預設值**：`0.05`
- **建議**：3-10%

### min_acceptable_price_ratio
- **說明**：最低可接受價格比例，不會低於原價的此比例
- **類型**：浮點數 (0.8 = 80%)
- **預設值**：`0.8`
- **建議**：70-90%

### quick_sell_price_ratio
- **說明**：快速銷售的價格比例，以市場價此比例快速出售
- **類型**：浮點數 (0.9 = 90%)
- **預設值**：`0.9`
- **建議**：85-95%

### quick_sell_trigger_hours
- **說明**：多少小時後觸發快速銷售
- **類型**：整數
- **預設值**：`12`
- **建議**：6-24小時

---

## 4. 風險管理配置 (risk_management)

### max_cash_investment_ratio
- **說明**：最大現金投資比例，最多投資此比例的現金
- **類型**：浮點數 (0.8 = 80%)
- **預設值**：`0.8`
- **建議**：
  - 保守：60-70%
  - 平衡：70-80%
  - 積極：80-90%

### emergency_cash_reserve
- **說明**：緊急現金儲備，始終保持的最低現金數額
- **類型**：浮點數
- **預設值**：`10000.0`
- **建議**：根據日常開支需求設定

### market_volatility_threshold
- **說明**：市場波動性閾值，超過此波動會暫停交易
- **類型**：浮點數 (0.4 = 40%)
- **預設值**：`0.4`
- **建議**：30-50%

### max_price_deviation
- **說明**：最大價格偏差，價格偏離此比例以上會停止該物品交易
- **類型**：浮點數 (0.3 = 30%)
- **預設值**：`0.3`
- **建議**：20-40%

### max_consecutive_failures
- **說明**：最大連續失敗次數，連續失敗此次數後會暫停交易
- **類型**：整數
- **預設值**：`3`
- **建議**：3-5次

### failure_cooldown_minutes
- **說明**：失敗後的冷卻時間（分鐘）
- **類型**：整數
- **預設值**：`5`
- **建議**：5-60分鐘

### anti_detection_enabled
- **說明**：是否啟用反檢測機制，模擬人類行為避免被系統檢測
- **類型**：布林值
- **預設值**：`true`
- **建議**：強烈建議保持開啟

### random_delay_range
- **說明**：隨機延遲範圍（秒），每個操作間的隨機等待時間
- **類型**：整數數組 [最短, 最長]
- **預設值**：`[2, 8]`
- **建議**：
  - 快速模式：[1, 3]
  - 標準模式：[2, 8]
  - 安全模式：[5, 15]

### max_operations_per_hour
- **說明**：每小時最大操作次數，限制操作頻率避免觸發反作弊
- **類型**：整數
- **預設值**：`50`
- **建議**：20-100次

---

## 5. 性能優化配置 (performance)

### market_cache_duration_minutes
- **說明**：市場數據緩存時間（分鐘），避免頻繁重複掃描
- **類型**：整數
- **預設值**：`1`
- **建議**：1-10分鐘

### price_cache_duration_minutes
- **說明**：價格數據緩存時間（分鐘）
- **類型**：整數
- **預設值**：`1`
- **建議**：1-15分鐘

### max_concurrent_operations
- **說明**：最大並發操作數，同時執行的操作數量
- **類型**：整數
- **預設值**：`3`
- **建議**：
  - 低配置：1-2
  - 標準配置：2-4
  - 高配置：4-6

### operation_timeout_seconds
- **說明**：單個操作的超時時間（秒）
- **類型**：整數
- **預設值**：`60`
- **建議**：30-120秒

### max_retries
- **說明**：操作失敗時的最大重試次數
- **類型**：整數
- **預設值**：`3`
- **建議**：2-5次

### retry_delay_seconds
- **說明**：重試間隔時間（秒）
- **類型**：整數
- **預設值**：`5`
- **建議**：3-10秒

### exponential_backoff
- **說明**：是否使用指數退避重試，每次重試延遲時間遞增
- **類型**：布林值
- **預設值**：`true`
- **建議**：建議開啟以避免過度重試

---

## 6. 全局設置

### trading_enabled
- **說明**：是否啟用自動交易功能
- **類型**：布林值
- **預設值**：`true`
- **用途**：總開關，可快速停止所有交易活動

### debug_mode
- **說明**：是否啟用調試模式，會輸出更詳細的日誌信息
- **類型**：布林值
- **預設值**：`false`
- **用途**：開發和問題排查時使用

### dry_run_mode
- **說明**：是否啟用模擬模式，只模擬交易不實際執行
- **類型**：布林值
- **預設值**：`false`
- **用途**：測試配置和策略時使用

### max_trading_cycles
- **說明**：最大交易週期數，執行完指定次數後自動停止
- **類型**：整數
- **預設值**：`0`（無限制）
- **建議**：根據需要調整，0 表示無限制

### cycle_interval_minutes
- **說明**：交易週期間隔時間（分鐘）
- **類型**：整數
- **預設值**：`10`
- **建議**：5-60分鐘

### session_timeout_hours
- **說明**：交易會話超時時間（小時）
- **類型**：整數
- **預設值**：`8`
- **建議**：4-12小時

### detailed_logging
- **說明**：是否啟用詳細日誌記錄
- **類型**：布林值
- **預設值**：`true`
- **建議**：建議開啟以便監控和分析

### log_all_market_data
- **說明**：是否記錄所有市場數據，會產生大量日誌
- **類型**：布林值
- **預設值**：`false`
- **建議**：僅在需要詳細市場分析時開啟

---

## 配置建議

### 新手設置
```json
{
  "market_search": {
    "target_items": ["12.7mm Rifle Bullets", "9mm Rifle Bullets"],
    "max_price_per_unit": [10.0, 10.0],
    "max_items_per_search": 10
  },
  "buying": {
    "min_profit_margin": 0.20,
    "max_purchases_per_cycle": 3
  },
  "risk_management": {
    "max_operations_per_hour": 20,
    "random_delay_range": [3, 10]
  }
}
```

### 標準設置（當前配置）
```json
{
  "market_search": {
    "target_items": ["12.7mm Rifle Bullets", "14mm Rifle Bullets", "9mm Rifle Bullets", "10 Gauge Shells", "12 Gauge Shells", "Energy Cell", "Gasoline"],
    "max_price_per_unit": [11.0, 13.0, 11.0, 15.0, 16.0, 15.0, 3.0],
    "max_items_per_search": 13
  },
  "buying": {
    "min_profit_margin": 0.15,
    "max_purchases_per_cycle": 10
  },
  "risk_management": {
    "max_operations_per_hour": 50,
    "random_delay_range": [2, 8]
  }
}
```

### 積極設置
```json
{
  "market_search": {
    "target_items": ["12.7mm Rifle Bullets", "14mm Rifle Bullets", "9mm Rifle Bullets", "10 Gauge Shells", "12 Gauge Shells", "Energy Cell", "Gasoline", "Pain Killers", "Antibiotics"],
    "max_price_per_unit": [15.0, 18.0, 15.0, 20.0, 20.0, 20.0, 5.0, 30.0, 40.0],
    "max_items_per_search": 20
  },
  "buying": {
    "min_profit_margin": 0.10,
    "max_purchases_per_cycle": 15
  },
  "risk_management": {
    "max_operations_per_hour": 80,
    "random_delay_range": [1, 5]
  }
}
```

---

## 配置管理

### 動態更新配置
```python
from dfautotrans.config.trading_config import TradingConfigManager

# 載入配置管理器
config_manager = TradingConfigManager()

# 更新特定配置
config_manager.update_config({
    "market_search.target_items": ["12.7mm Rifle Bullets", "9mm Rifle Bullets"],
    "market_search.max_price_per_unit": [13.0, 15.0],
    "buying.min_profit_margin": 0.20,
    "selling.markup_percentage": 0.30
})

# 保存配置
config_manager.save_config()
```

### 配置驗證
系統會自動驗證配置的有效性：
- 數值範圍檢查
- 數組長度一致性驗證（target_items 與 max_price_per_unit）
- 邏輯一致性驗證
- 必要參數檢查

### 配置備份
建議定期備份配置文件：
```bash
cp trading_config.json trading_config_backup_$(date +%Y%m%d).json
```

---

## 重要變更說明

### 1. 精確匹配策略
- 系統現在只會購買 `target_items` 中完全匹配的物品
- 移除了 `excluded_items`，通過精確匹配避免誤買
- 搜索更加精準和高效

### 2. 個性化價格設定
- `max_price_per_unit` 現在是數組，與 `target_items` 一一對應
- 每種物品可以設定不同的最高價格
- 提供更靈活的價格控制

### 3. 簡化配置結構
- 移除了複雜的持有時間和動態調價機制
- 移除了市場波動檢測和投資限制
- 保留核心功能，提高配置效率
- 更容易理解和維護

### 4. 多樣化投資
- `diversification_enabled` 控制是否啟用多樣化投資策略
- 避免過度集中投資單一物品類型
- 降低市場風險

---

## 注意事項

1. **數組對應**：確保 `target_items` 和 `max_price_per_unit` 數組長度相同
2. **精確匹配**：物品名稱必須完全匹配，注意大小寫和空格
3. **價格設定**：根據市場情況定期調整各物品的最高價格
4. **風險控制**：雖然簡化了配置，仍需保持適當的風險控制
5. **測試優先**：新配置先在模擬模式下測試

---

## 常見問題

### Q: 為什麼某些物品沒有被購買？
A: 檢查 `target_items` 中的物品名稱是否與遊戲中完全匹配，以及對應的 `max_price_per_unit` 是否合理。

### Q: 如何添加新的目標物品？
A: 在 `target_items` 數組中添加新物品名稱，同時在 `max_price_per_unit` 數組的相同位置添加對應價格。

### Q: 配置更改後何時生效？
A: 大部分配置會在下一個交易週期生效，價格和目標物品的變更會立即生效。

### Q: 如何確保配置正確？
A: 系統會自動驗證配置，特別是數組長度的一致性。如有錯誤會在啟動時提示。

### Q: diversification_enabled 是什麼？
A: 多樣化投資策略，啟用後會避免過度購買同類型物品，降低集中投資風險。 