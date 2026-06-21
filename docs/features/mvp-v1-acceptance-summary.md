# MVP 第一版總驗收摘要

本文件提供給驗收 thread 直接使用。  
目標是用單一文件完成 MVP 第一版的總驗收盤點、操作步驟與已知限制確認。

## 驗收範圍

本次 MVP 第一版總驗收涵蓋：

1. 股票查詢
2. 自訂日期區間
3. 收盤價走勢圖
4. MA5 / MA20
5. 收藏清單
6. 模擬 BUY / SELL
7. 交易紀錄
8. 持股總覽
9. 已實現損益
10. 未實現損益與市值
11. 投資組合摘要

## 驗收前準備

### 安裝與啟動

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 自動化測試

```bash
python -m unittest discover -s tests -v
```

選配 smoke test：

```bash
set RUN_TWSE_SMOKE=1
python -m unittest discover -s tests -p "test_stock_price_smoke.py" -v
```

## MVP 功能總表

| 功能 | 目前狀態 | 主要頁面 / 路由 | 驗收重點 |
| --- | --- | --- | --- |
| 股票查詢 | 已完成 | `/`、`/stocks/search` | 可查單一股票並顯示基本資料與歷史價格 |
| 自訂日期區間 | 已完成 | `/`、`/stocks/search` | 開始日期、結束日期可控制查詢區間，錯誤日期有提示 |
| 收盤價走勢圖 | 已完成 | `/stocks/search` | 查詢成功時可顯示收盤價 SVG 圖 |
| MA5 / MA20 | 已完成 | `/stocks/search` | 表格與圖表可顯示 MA5 / MA20 |
| 收藏清單 | 已完成 | `/watchlist` | 可新增、查看、移除，且防止重複加入 |
| 模擬 BUY / SELL | 已完成 | `/stocks/search`、`/trades/portfolio` | 可建立 BUY / SELL，並檢查資金與持股 |
| 交易紀錄 | 已完成 | `/trades` | 顯示 BUY / SELL、新到舊排序、SELL 已實現損益 |
| 持股總覽 | 已完成 | `/trades/portfolio` | 顯示持股數量、平均成本、持股成本基礎 |
| 已實現損益 | 已完成 | `/trades` | 顯示每筆 SELL 與累計已實現損益 |
| 未實現損益與市值 | 已完成 | `/trades/portfolio` | 顯示最近價格、估算市值、未實現損益 |
| 投資組合摘要 | 已完成 | `/trades/portfolio` | 顯示現金、市值、已實現 / 未實現損益與總資產估值 |

## 建議人工驗收流程

### 1. 股票查詢與圖表

1. 開啟首頁 `/`
2. 輸入 `2330`
3. 輸入開始日期與結束日期，例如 `2024-05-01` 到 `2024-05-31`
4. 送出查詢
5. 確認：
   - 有股票名稱與代號
   - 有歷史資料表格
   - 有收盤價走勢圖
   - 有 MA5 / MA20

### 2. 日期錯誤處理

1. 輸入開始日期晚於結束日期
2. 或輸入錯誤日期格式
3. 確認頁面顯示專案自己的錯誤提示，不是框架預設錯誤頁

### 3. 收藏清單

1. 在股票查詢結果頁加入收藏
2. 前往 `/watchlist`
3. 確認：
   - 看得到股票代號、股票名稱、建立時間
   - 可移除
   - 重複加入時有提示

### 4. 模擬買進

1. 在股票查詢結果頁輸入買進價格、股數、時間
2. 送出 BUY
3. 確認：
   - 有成功訊息
   - `/trades` 可看到 BUY 紀錄
   - `/trades/portfolio` 可看到持股

### 5. 模擬賣出

1. 在 `/trades/portfolio` 對已持有股票輸入賣出資料
2. 送出 SELL
3. 確認：
   - `/trades` 可看到 SELL 紀錄
   - 持股數量有扣減
   - 賣出超過持股時有明確錯誤提示

### 6. 交易紀錄與已實現損益

前往 `/trades`，確認：

1. 交易新到舊排序
2. 顯示股票代號、股票名稱、交易類型、價格、股數、時間、總金額
3. SELL 顯示已實現損益
4. 頁面摘要顯示累計已實現損益

### 7. 持股總覽、未實現損益與投資組合摘要

前往 `/trades/portfolio`，確認：

1. 顯示持股數量、平均成本、持股成本基礎
2. 顯示目前價格、估算市值、未實現損益
3. 頁面上方顯示：
   - 初始虛擬資金
   - 目前可用資金
   - 目前已使用資金
   - 目前持股市值
   - 累計已實現損益
   - 整體未實現損益
   - 目前總資產估值
4. 驗證公式：
   - `總資產估值 = 可用資金 + 持股市值`

## 最小自動化驗收參考

主要驗證：

```bash
python -m unittest discover -s tests -v
```

預期：

1. 一般單元測試全數通過
2. `test_stock_price_smoke.py` 預設為 `skipped`
3. 不因真實外部資料測試影響主測試穩定性

真實價格路徑補強驗證：

```bash
set RUN_TWSE_SMOKE=1
python -m unittest discover -s tests -p "test_stock_price_smoke.py" -v
```

預期：

1. 測試會實際打到 TWSE
2. 可取得非空且格式合理的最近收盤價
3. 可驗證向前回補查找邏輯

## 已知限制

1. 僅支援單一股票查詢
2. 目前價格使用最近可取得收盤價，不是即時報價
3. 技術指標僅有 MA5 / MA20
4. 不含手續費、交易稅、零股、當沖與進階交易規則
5. 無使用者登入與多使用者隔離
6. 無正式部署到外網的完整流程
7. 無完整 API 文件與資料庫設計文件

## MVP 第一版可結案判斷建議

若以下條件皆成立，可判定 MVP 第一版可結案：

1. 主要功能總表所列項目皆可依人工流程操作成功
2. `python -m unittest discover -s tests -v` 通過
3. README 與 docs 可支援啟動、操作與展示說明
4. 已完成 / 未完成邊界清楚
5. 沒有阻擋展示與交接的重大問題

## 交接給驗收 thread 的建議用語

可直接以這份文件作為總驗收主文件，並搭配：

1. `README.md`
2. `docs/mvp-plan.md`
3. `docs/features/current-mvp-features.md`

若驗收 thread 發現問題，建議先區分：

1. 功能缺口
2. 文件落差
3. 外部資料不穩定
4. 展示流程不清楚
