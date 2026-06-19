# 專案資料夾結構與模組責任分工

## 一、建議資料夾結構

```text
taiwan-stock-analysis/
├─ app/
│  ├─ main.py
│  ├─ config.py
│  ├─ database.py
│  ├─ models/
│  │  ├─ stock.py
│  │  ├─ watchlist.py
│  │  ├─ trade.py
│  │  └─ __init__.py
│  ├─ schemas/
│  │  ├─ stock.py
│  │  ├─ watchlist.py
│  │  ├─ trade.py
│  │  └─ __init__.py
│  ├─ routers/
│  │  ├─ pages.py
│  │  ├─ stocks.py
│  │  ├─ watchlist.py
│  │  ├─ trades.py
│  │  └─ __init__.py
│  ├─ services/
│  │  ├─ stock_service.py
│  │  ├─ indicator_service.py
│  │  ├─ watchlist_service.py
│  │  ├─ trade_service.py
│  │  └─ portfolio_service.py
│  ├─ repositories/
│  │  ├─ stock_repository.py
│  │  ├─ watchlist_repository.py
│  │  ├─ trade_repository.py
│  │  └─ __init__.py
│  ├─ templates/
│  │  ├─ base.html
│  │  ├─ index.html
│  │  ├─ stock_detail.html
│  │  ├─ watchlist.html
│  │  ├─ portfolio.html
│  │  └─ trades.html
│  ├─ static/
│  │  ├─ css/
│  │  │  └─ style.css
│  │  └─ js/
│  │     └─ main.js
│  └─ utils/
│     ├─ helpers.py
│     ├─ date_utils.py
│     └─ __init__.py
├─ data/
│  └─ app.db
├─ tests/
│  ├─ test_stocks.py
│  ├─ test_watchlist.py
│  └─ test_trades.py
├─ docs/
│  ├─ project-spec.md
│  ├─ api-design.md
│  ├─ database-design.md
│  ├─ deployment.md
│  ├─ finance-notes.md
│  └─ learning-log.md
├─ .env
├─ .env.example
├─ requirements.txt
├─ README.md
└─ run.py
```

## 二、每個資料夾的用途

## `app/`

專案主程式區，幾乎所有核心程式都放這裡。

## `app/main.py`

系統入口。負責：

1. 建立 FastAPI app
2. 載入 routers
3. 掛載靜態檔案
4. 設定模板引擎

你可以把它想成整個網站的啟動中心。

## `app/config.py`

集中管理設定值，例如：

1. 資料庫路徑
2. API 金鑰
3. 環境變數
4. 預設查詢天數

這樣之後改設定不用到處找。

## `app/database.py`

負責資料庫連線與初始化，例如：

1. 建立 SQLite 連線
2. 提供 Session
3. 初始化資料表

## `app/models/`

放資料表模型。如果之後用 SQLAlchemy，這裡就是定義資料表的地方。

例如：

- `stock.py`：股票基本資料表
- `watchlist.py`：收藏清單資料表
- `trade.py`：模擬交易資料表

它負責的是「資料長什麼樣」。

## `app/schemas/`

放 API 輸入輸出格式，通常會用 Pydantic 來定義。

例如：

- 建立收藏時要傳什麼欄位
- 買入股票時表單要有哪些欄位
- API 回傳格式長什麼樣

它負責的是「資料怎麼進來、怎麼出去」。

## `app/routers/`

放路由，也就是網址對應的功能入口。

例如：

- `pages.py`：網頁頁面路由
- `stocks.py`：股票查詢 API
- `watchlist.py`：收藏功能 API
- `trades.py`：模擬交易 API

它負責的是「收到請求後，把事情交給誰做」。

## `app/services/`

這層很重要，放商業邏輯，也就是系統真正的功能處理。

例如：

- `stock_service.py`：抓股票資料、整理資料
- `indicator_service.py`：計算 MA5、MA20
- `watchlist_service.py`：處理收藏新增刪除
- `trade_service.py`：處理買賣交易
- `portfolio_service.py`：計算持股、成本、損益

它負責的是「這個功能實際怎麼運作」。

## `app/repositories/`

放資料存取邏輯，也就是把資料寫進資料庫、從資料庫讀出來。

例如：

- 新增收藏
- 查詢交易紀錄
- 取得持股資料

它負責的是「怎麼跟資料庫講話」。

如果你是新手，第一版也可以先不拆這層太細，先把簡單資料庫操作放在 service 裡。  
但如果你想讓架構更清楚，保留這層會很好。

## `app/templates/`

放 HTML 頁面模板。如果你用 `FastAPI + Jinja2`，畫面會放這裡。

例如：

- `index.html`：首頁
- `stock_detail.html`：個股頁
- `watchlist.html`：收藏頁
- `portfolio.html`：持股與損益頁
- `trades.html`：交易紀錄頁

## `app/static/`

放靜態資源，例如：

- CSS 樣式
- JavaScript
- 圖片

第一版先簡單即可，不要花太多時間做前端特效。

## `app/utils/`

放共用小工具，例如：

- 日期轉換
- 格式化數字
- 共用 helper 函式

這裡放「小而通用」的東西，不要把核心商業邏輯塞進來。

## `data/`

放本機資料。第一版可以先放：

- `app.db`：SQLite 資料庫

如果之後改 PostgreSQL，這裡的角色就會變小。

## `tests/`

放測試程式。第一版不需要全做，但至少可以保留位置。

建議先測：

1. 股票查詢是否正常
2. 收藏新增刪除是否正常
3. 模擬交易計算是否正常

## `docs/`

放專案文件。這對作品集很重要。

建議至少有：

1. 專案規格
2. API 設計
3. 資料庫設計
4. 部署說明
5. 金融知識補充
6. 學習紀錄

## 三、模組責任分工

### 1. `stocks` 模組

負責：

1. 接收股票代號查詢
2. 串接外部資料來源
3. 整理歷史股價資料
4. 回傳給頁面或 API
5. 提供圖表所需資料

適合練習：

1. requests
2. pandas
3. JSON 解析
4. 函式拆分

### 2. `indicator` 模組

負責：

1. 計算 MA5
2. 計算 MA20
3. 整理技術指標欄位
4. 供圖表或表格顯示

適合練習：

1. pandas rolling
2. 欄位計算
3. 資料前處理

### 3. `watchlist` 模組

負責：

1. 加入收藏
2. 移除收藏
3. 查詢收藏清單

適合練習：

1. CRUD
2. 路由設計
3. 資料表操作

### 4. `trades` 模組

負責：

1. 模擬買進
2. 模擬賣出
3. 儲存交易紀錄
4. 基本交易檢查
5. 避免賣出超過持股

適合練習：

1. 條件判斷
2. 交易邏輯
3. 例外處理
4. 商業規則整理

### 5. `portfolio` 模組

負責：

1. 彙總目前持股
2. 計算平均成本
3. 計算未實現損益
4. 計算已實現損益
5. 整理投資組合頁面資料

適合練習：

1. groupby
2. 聚合計算
3. 邏輯拆分
4. 查詢結果整理

### 6. `pages` 模組

負責：

1. 首頁顯示
2. 個股查詢頁
3. 收藏頁
4. 交易紀錄頁
5. 持股總覽頁

這一層主要是讓你的作品能被看見、被操作。

## 四、建議的責任分層原則

你可以用這個簡單原則記：

1. `router`：接請求
2. `service`：做邏輯
3. `repository`：碰資料庫
4. `model`：定義資料表
5. `schema`：定義輸入輸出
6. `template`：顯示畫面

如果之後寫到一半分不清該放哪，就用這個原則判斷。

## 五、對新手最實用的簡化建議

雖然上面架構是推薦版，但你第一版其實可以先適度簡化。

### 可以先簡化的地方

1. `repositories/` 可以先不拆太細
2. `tests/` 可以先只寫最小範圍
3. `utils/` 不要一開始放太多東西
4. `schemas/` 先只寫真的有用到的輸入輸出格式

### 不建議省略的地方

1. `routers/`
2. `services/`
3. `templates/`
4. `models/`
5. `docs/`

因為這幾個最能幫你養成好結構。

## 六、你第一版最推薦的實作順序

依照資料夾與模組，我建議順序是：

1. 建 `app/main.py`
2. 建 `routers/pages.py`
3. 建 `templates/index.html`
4. 建 `services/stock_service.py`
5. 完成股票查詢功能
6. 建 `models/` 與 `database.py`
7. 完成 `watchlist` 功能
8. 完成 `trades` 功能
9. 完成 `portfolio` 功能
10. 最後補 `docs/` 與 `tests/`
