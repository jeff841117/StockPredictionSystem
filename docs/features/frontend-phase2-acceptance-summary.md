# 前端第二階段總驗收摘要

本文件作為 `main = 作品集版第二階段主線` 的單一驗收入口。  
用途是讓驗收 thread 可依同一份摘要，完成首頁與個股頁前端第二階段成果的總檢查。

## 驗收範圍

本輪前端第二階段已完成的展示型主線成果：

1. `Research Summary` 區
2. 首頁 `Screener / Research Candidates` 展示區
3. 研究工作台版位優化
4. 圖表疊層切換
5. Demo 用投資組合摘要強化

不納入本輪驗收的內容：

1. `daily-use` 分支候選功能
2. 新的交易規則或投資組合商業邏輯
3. 即時行情
4. 更多技術指標
5. 個人化偏好記憶

## 主線定位

目前已定案：

1. `main = 作品集版第二階段主線`
2. `daily-use = 未來分支方向`

因此本輪驗收應以「展示力、研究感、作品集敘事清楚度」為主，不以高頻個人工具效率為主要判準。

## 已完成功能總表

### 1. 個股頁 `Research Summary`

頁面：

1. `app/templates/stock_detail.html`

目前可見內容：

1. 股票名稱與代號
2. 查詢區間
3. 最新收盤價
4. 區間漲跌與漲跌幅
5. 區間高低
6. 最新 `MA5 / MA20`
7. 持股狀態、持股數量、平均成本

驗收重點：

1. 成功查詢時摘要資料與表格、圖表一致
2. 無持股時文案清楚，不造成版面錯亂
3. 不帶投資建議語句

### 2. 首頁 `Research Candidates / Screener` 展示區

頁面：

1. `app/templates/index.html`

目前可見內容：

1. 少量研究候選股列表
2. 股票代號、名稱、最新收盤價
3. 區間漲跌 / 漲跌幅
4. `MA5 / MA20` 狀態摘要
5. 導向既有個股研究頁

驗收重點：

1. 區塊定位清楚為研究候選展示，不是假裝成即時全市場掃描器
2. 每筆候選可導向既有個股頁
3. 部分資料失敗時仍有 fallback，不讓首頁崩潰

### 3. 研究工作台版位優化

頁面：

1. `app/templates/index.html`
2. `app/templates/stock_detail.html`
3. `app/static/css/style.css`

目前版位節奏：

1. 首頁：查詢入口 + 研究流程側欄 + Screener 展示 + 功能定位
2. 個股頁：研究摘要 + 圖表主區 + 右側操作欄 + 下方歷史資料表

驗收重點：

1. 桌面版閱讀順序清楚
2. 主要資訊不再只是堆疊
3. 手機版可正常收成單欄

### 4. 圖表疊層切換

頁面：

1. `app/templates/stock_detail.html`
2. `app/static/css/style.css`

目前可切換圖層：

1. 收盤價
2. `MA5`
3. `MA20`

驗收重點：

1. 預設三者都顯示
2. 使用者可切換顯示 / 隱藏
3. 切換不影響表格、摘要與後端資料
4. 資料不足時不應誤顯示切換控制

### 5. Demo 用投資組合摘要強化

頁面：

1. `app/templates/index.html`
2. `app/templates/portfolio.html`

目前可見成果：

1. 首頁精簡版 `Portfolio Workspace` preview
2. 持股頁以 `Cash / Holdings / PnL` 分組的展示型摘要
3. 總資產估值主卡
4. 缺價 fallback 提示

驗收重點：

1. 首頁 preview 不應搶掉 Screener 主視覺
2. 持股頁能一眼看懂現金、部位、市值、損益關係
3. 缺價提示明確，不讓人誤判成計算錯誤

## 建議人工驗收路徑

### A. 首頁

1. 開啟 `/`
2. 檢查 `Stock Screener Workspace` hero
3. 檢查 `Core Search`
4. 檢查 `Research Flow`
5. 檢查 `Research Candidates`
6. 檢查 `Portfolio Workspace` preview

應確認：

1. 查詢入口仍可正常使用
2. Screener 區有研究候選清單
3. Portfolio preview 有清楚的現金 / 部位 / 損益摘要
4. 有前往完整持股頁的入口

### B. 個股頁

建議用：

1. `/stocks/search?stock_no=2330&start_date=2024-05-01&end_date=2024-05-31`

應確認：

1. `Research Summary` 正常顯示
2. 圖表區有圖層切換控制
3. 切換 `收盤價 / MA5 / MA20` 不會讓頁面錯誤
4. 右側操作欄仍包含收藏與模擬買進
5. 歷史資料表在下方全寬區

### C. 持股頁

開啟：

1. `/trades/portfolio`

應確認：

1. `Portfolio Summary` 已拆成總資產主卡 + `Cash / Holdings / PnL`
2. 若目前無持股，空狀態仍可理解
3. 若有持股，摘要與持股表資料關係一致
4. 若缺價，fallback 提示仍清楚存在

## 已知限制

本輪前端第二階段仍未包含：

1. `daily-use` 的最近查詢、快捷區間、個人化偏好
2. 完整多條件 screener 後端
3. 即時行情
4. 更多技術指標
5. 進階圖表互動

這些應視為目前版本的明確界線，不應直接判定為 bug。

## 驗證依據

本輪開發已執行的最小驗證包含：

1. `python -m unittest tests/test_stocks.py -v`
2. `python -m unittest tests/test_trades.py -v`
3. `python -m unittest discover -s tests -v`
4. 首頁、個股頁、持股頁的最小人工畫面檢查

## 可交給驗收 thread 的判讀重點

驗收 thread 建議輸出至少包含：

1. 驗收依據
2. 通過項目
3. 未通過項目
4. 已知限制
5. 是否可作為前端第二階段主線收尾版本結案
