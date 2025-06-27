# Dead Frontier 自動交易系統 - 運行指南

## 🚀 項目啟用和運行指南

### 📦 關於 uv 包管理器

本項目使用 **uv** - 一個極快的 Python 包管理器，提供以下優勢：

- **🚀 極快速度**：比 pip 快 10-100 倍
- **🔒 可靠性**：確定性依賴解析和鎖定文件
- **🛠️ 簡化工作流**：一個工具管理虛擬環境、依賴和腳本運行
- **💾 磁盤效率**：全局緩存避免重複下載

**為什麼選擇 uv？**
- 更快的依賴安裝和解析
- 自動虛擬環境管理
- 與 pip 和 Poetry 兼容
- 內建項目腳本運行功能

### 1. 環境準備

#### 必要軟件
- Python 3.11+
- uv 包管理器
- Google Chrome 瀏覽器
- 穩定的網絡連接

#### 安裝 uv 包管理器
```bash
# 安裝 uv（如果尚未安裝）
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# 或使用 pip
pip install uv
```

#### 設置項目環境
```bash
# 確保在項目根目錄
cd Dfautotrans

# 使用 uv 同步依賴（推薦）
uv sync

# 這會自動：
# 1. 創建虛擬環境（如果不存在）
# 2. 安裝所有依賴項
# 3. 確保版本一致性
```

### 2. 配置設置

#### 環境變量配置
1. 複製環境變量模板：
```bash
cp env.example .env
```

2. 編輯 `.env` 文件，填入您的配置：
```env
# Dead Frontier 登錄信息
DF_USERNAME=your_username
DF_PASSWORD=your_password

# 瀏覽器設置
HEADLESS_MODE=false  # 設為 true 可無頭運行
BROWSER_TIMEOUT=30000

# 日誌設置
LOG_LEVEL=INFO
```

#### 交易配置
編輯 `trading_config.json` 文件來自定義交易策略：

```json
{
  "target_items": {
    "12.7mm Pistol Ammo": {
      "max_price": 50.0,
      "target_price": 65.0,
      "priority": 1
    },
    "Painkillers": {
      "max_price": 120.0,
      "target_price": 150.0,
      "priority": 2
    }
  },
  "risk_management": {
    "max_purchase_amount": 50000,
    "min_profit_margin": 0.20,
    "normal_wait_seconds": 300,
    "blocked_wait_seconds": 1800
  }
}
```

### 3. 運行項目

#### 方法 1：持續自動交易（生產環境推薦）
```bash
# 使用 uv 運行持續交易系統 - 真正的24/7自動交易
uv run continuous_trading_system.py
```

#### 方法 2：單週期測試（測試推薦）
```bash
# 使用 uv 測試單個交易週期（含詳細日誌）
uv run demo_stage3_with_detailed_logging.py
```

#### 方法 3：交易引擎測試
```bash
# 使用 uv 測試交易引擎基本功能
uv run demo_stage3_trading_engine.py
```

#### 方法 4：分步功能測試
```bash
# 測試登錄功能
uv run demo_stage2_smart_login_and_goto_bank.py

# 測試市場掃描
uv run demo_market_scan.py

# 測試庫存管理
uv run demo_stage2_inventory.py
```

#### ⚠️ 注意：main.py 目前無法使用
```bash
# ❌ 此文件引用了不存在的模組，無法運行
# python main.py  # 不要使用這個
```

### 4. 監控和日誌

#### 日誌文件位置
- `logs/detailed_trading.log` - 詳細的人類可讀日誌
- `logs/trading_data.jsonl` - 結構化交易數據
- `logs/dfautotrans.log` - 系統日誌
- `logs/browser.log` - 瀏覽器操作日誌
- `logs/errors.log` - 錯誤日誌

#### 實時監控
```bash
# 監控詳細交易日誌
tail -f logs/detailed_trading.log

# 監控系統日誌
tail -f logs/dfautotrans.log

# 監控錯誤日誌
tail -f logs/errors.log
```

### 5. 高級運行選項

#### 無頭模式運行（服務器環境）
```bash
# 設置環境變量
export HEADLESS_MODE=true

# 使用 uv 運行
uv run demo_stage3_with_detailed_logging.py
```

#### 開發模式運行
```bash
# 安裝開發依賴
uv sync --group dev

# 運行測試
uv run pytest

# 代碼格式化
uv run black src/
uv run ruff check src/
```

#### 虛擬環境管理
```bash
# 激活 uv 管理的虛擬環境
# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

# 在激活的環境中直接運行
python continuous_trading_system.py

# 退出虛擬環境
deactivate
```

### 6. 系統狀態檢查

#### 檢查系統健康狀態
```bash
# 運行系統測試
uv run pytest tests/ -v

# 檢查瀏覽器環境
uv run python -c "
from src.dfautotrans.automation.browser_manager import BrowserManager
from src.dfautotrans.config.settings import Settings
import asyncio

async def test_browser():
    settings = Settings()
    browser = BrowserManager(settings)
    await browser.initialize()
    print('✅ 瀏覽器初始化成功')
    await browser.cleanup()

asyncio.run(test_browser())
"
```

#### 檢查配置文件
```bash
# 驗證交易配置
uv run python -c "
from src.dfautotrans.config.trading_config import TradingConfigManager
manager = TradingConfigManager('trading_config.json')
config = manager.load_config()
errors = manager.validate_config()
if errors:
    print('❌ 配置錯誤:', errors)
else:
    print('✅ 配置文件有效')
"
```

#### 依賴管理
```bash
# 查看已安裝的依賴
uv tree

# 更新依賴
uv sync --upgrade

# 添加新依賴
uv add package_name

# 移除依賴
uv remove package_name

# 查看過時的依賴
uv tree --outdated
```

### 7. 常見問題和解決方案

#### 問題 1：瀏覽器無法啟動
```bash
# 解決方案：安裝 Playwright 瀏覽器
uv run playwright install chromium

# 或安裝所有瀏覽器
uv run playwright install
```

#### 問題 2：登錄失敗
- 檢查 `.env` 文件中的用戶名和密碼
- 確認 Dead Frontier 網站可正常訪問
- 檢查是否有驗證碼或其他登錄限制

#### 問題 3：交易配置錯誤
```bash
# 重置為默認配置
cp trading_config.json.backup trading_config.json
```

#### 問題 4：權限問題
```bash
# 確保日誌目錄可寫
mkdir -p logs
chmod 755 logs
```

### 8. 性能優化建議

#### 調整等待時間
在 `trading_config.json` 中調整：
```json
{
  "risk_management": {
    "normal_wait_seconds": 180,     // 縮短正常等待時間
    "blocked_wait_seconds": 900,    // 縮短阻塞等待時間
    "max_login_retries": 3
  }
}
```

#### 調整市場掃描參數
```json
{
  "market_search": {
    "max_items_per_search": 20,     // 增加掃描物品數量
    "primary_search_terms": ["12.7", "Painkiller", "Bandage"]
  }
}
```

### 9. 監控和維護

#### 設置定時任務（Linux/Mac）
```bash
# 編輯 crontab
crontab -e

# 添加定時任務（每小時運行一次）
0 * * * * cd /path/to/Dfautotrans && python demo_stage3_with_detailed_logging.py >> logs/cron.log 2>&1
```

#### 設置定時任務（Windows）
使用任務計劃程序創建定時任務，運行：
```cmd
cd C:\path\to\Dfautotrans && python demo_stage3_with_detailed_logging.py
```

### 10. 安全注意事項

1. **不要分享登錄信息**：確保 `.env` 文件不被提交到版本控制
2. **定期更新密碼**：建議定期更改 Dead Frontier 密碼
3. **監控異常活動**：定期檢查交易日誌，確保沒有異常行為
4. **備份數據**：定期備份 `dfautotrans.db` 和配置文件

### 11. 獲取幫助

如果遇到問題：
1. 檢查 `logs/errors.log` 文件
2. 查看詳細的交易日誌 `logs/detailed_trading.log`
3. 運行測試命令確認各組件工作正常
4. 檢查配置文件格式是否正確

---

## 🎯 快速開始命令

### 🚀 生產環境（持續交易）
```bash
# 1. 安裝 uv 包管理器（如果尚未安裝）
curl -LsSf https://astral.sh/uv/install.sh | sh  # macOS/Linux
# 或 Windows PowerShell: powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# 2. 同步依賴
uv sync

# 3. 配置環境
cp env.example .env
# 編輯 .env 文件填入登錄信息

# 4. 安裝瀏覽器
uv run playwright install chromium

# 5. 運行持續交易系統
uv run continuous_trading_system.py

# 6. 監控日誌
tail -f logs/continuous_trading.log
```

### 🧪 測試環境（單次運行）
```bash
# 1. 安裝 uv 包管理器（如果尚未安裝）
curl -LsSf https://astral.sh/uv/install.sh | sh  # macOS/Linux
# 或 Windows PowerShell: powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# 2. 同步依賴
uv sync

# 3. 配置環境
cp env.example .env
# 編輯 .env 文件填入登錄信息

# 4. 安裝瀏覽器
uv run playwright install chromium

# 5. 測試單個週期
uv run demo_stage3_with_detailed_logging.py

# 6. 監控日誌
tail -f logs/detailed_trading.log
```

現在您的 Dead Frontier 自動交易系統已經準備就緒！🚀 