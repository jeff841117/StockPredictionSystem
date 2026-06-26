# 資料隔離最小版 migration 規格

本文件用來支援「資料隔離最小版」實作前的資料表升級規格整理。  
目標是先把 SQLite 下的升級原則、舊資料處理方式與驗收基準寫清楚，避免下一輪直接改 `user_id` 時出現判讀不一致。

## 1. 本文件定位

這份文件只處理：

1. `users / watchlist / trades` 的最小 schema 升級規格
2. `user_id` 導入時的舊資料相容策略
3. 空資料庫與既有資料庫的升級方式
4. 下一輪驗收時應確認的 migration 情境

這份文件不處理：

1. Alembic 或完整 migration framework 導入
2. PostgreSQL 升級
3. 權限模型或角色設計
4. 更大範圍的資料庫重構藍圖

## 2. 目前資料表現況

目前專案使用 SQLite，核心資料表如下：

### `users`

用途：

1. 保存最小登入帳號資料

目前最小欄位：

1. `id`
2. `username`
3. `password_hash`
4. `created_at`

### `watchlist`

用途：

1. 保存收藏股票清單

原始最小欄位設計：

1. `stock_no`
2. `stock_name`
3. `created_at`

原始風險：

1. 沒有 `user_id`
2. 收藏資料為全域共用
3. 重複規則只能做全域唯一，無法做使用者內唯一

### `trades`

用途：

1. 保存模擬 BUY / SELL 交易資料

原始最小欄位設計：

1. `id`
2. `stock_no`
3. `stock_name`
4. `trade_type`
5. `price`
6. `quantity`
7. `trade_time`
8. `total_amount`

原始風險：

1. 沒有 `user_id`
2. 交易、持股、損益與投資組合摘要都會變成全域混算

## 3. 本輪 schema 變更目標

資料隔離最小版需要的最小變更如下：

### `users`

本輪不新增欄位，沿用既有最小登入表。

### `watchlist`

需要新增：

1. `id`
2. `user_id`

需要改變：

1. 原本以 `stock_no` 做全域唯一
2. 改為 `(user_id, stock_no)` 做使用者內唯一

升級後最小語意：

1. 同一使用者不能重複收藏同一股票
2. 不同使用者可以各自收藏相同股票

### `trades`

需要新增：

1. `user_id`

升級後最小語意：

1. 每筆 BUY / SELL 都要有明確 user 歸屬
2. `trades` 的 user scope 會直接影響：
   - 交易紀錄
   - 持股總覽
   - 已實現損益
   - 未實現損益
   - 投資組合摘要

## 4. 空資料庫升級策略

若是全新安裝、尚未建立任何資料：

1. 直接建立新版本 schema
2. `users`、`watchlist`、`trades` 一開始就以含 `user_id` 的版本建立
3. 不需要額外搬移步驟

空資料庫的判定：

1. `watchlist` 不存在
2. `trades` 不存在
3. 或整個 SQLite 檔案不存在

這是最單純、風險最低的情境。

## 5. 既有資料庫升級策略

若本機已存在舊版 SQLite，且：

1. 已有 `watchlist`
2. 已有 `trades`
3. 但尚未有 `user_id`

則本輪採以下最小升級策略。

### 5.1 `watchlist` 升級原則

因為 SQLite 對既有唯一鍵 / 主鍵變更不適合用單純 `ALTER COLUMN` 處理，所以採：

1. 重新建立新表
2. 搬移舊資料
3. 移除舊表

建議步驟：

1. 將舊 `watchlist` 重新命名為 `watchlist_legacy`
2. 建立含 `id`、`user_id`、`UNIQUE(user_id, stock_no)` 的新 `watchlist`
3. 依舊資料相容策略決定 `user_id`
4. 將舊資料搬入新表
5. 確認搬移完成後刪除 `watchlist_legacy`

### 5.2 `trades` 升級原則

因為 `trades` 需要新增 `user_id`，且後續所有損益 / 持股推導都依賴這個欄位，建議同樣採：

1. 重新建立新表
2. 搬移舊資料
3. 移除舊表

建議步驟：

1. 將舊 `trades` 重新命名為 `trades_legacy`
2. 建立含 `user_id` 的新 `trades`
3. 依舊資料相容策略決定 `user_id`
4. 將舊資料搬入新表
5. 確認搬移完成後刪除 `trades_legacy`

## 6. `user_id` 導入時的舊資料處理策略

這一段是下一輪最容易出現歧義的地方，因此要先寫死規則。

### 6.1 預設前提

舊版專案在資料隔離前，`watchlist` 與 `trades` 都屬於「單使用者視角」資料。  
也就是說，舊資料雖然沒有 `user_id`，但在產品語意上可視為「某一位本地使用者過去留下的資料」。

### 6.2 最小相容策略

若升級時：

1. 資料庫內至少已有一位使用者

則：

1. 將舊 `watchlist` 與 `trades` 全部歸屬給「第一位既有使用者」
2. 這個「第一位」規則建議固定為 `users.id` 最小者

這樣做的理由：

1. 符合舊版單使用者展示的歷史脈絡
2. 不需要在本輪引入人工對應介面
3. 可讓舊資料在最小成本下保留下來

### 6.3 若舊資料存在但 `users` 為空

若升級時：

1. `watchlist` 或 `trades` 有資料
2. 但 `users` 表為空

本輪規格建議：

1. 不自動虛構匿名使用者
2. 不把資料硬塞到不存在的 `user_id`
3. 允許這批舊資料暫時不搬移，或保留在 legacy 表待人工處理

原因：

1. 本輪不做完整 migration framework
2. 也不做資料修復 UI
3. 若直接虛構帳號，會模糊登入與資料歸屬規則

因此應在升級紀錄或文件中明確標示：

1. 這屬於「異常舊資料情境」
2. 需要人工決定要先建帳號再搬移，或放棄舊資料

### 6.4 同名股票的唯一性規則

升級後以 `(user_id, stock_no)` 為唯一規則：

1. 使用者 A 可收藏 `2330`
2. 使用者 B 也可收藏 `2330`
3. 但使用者 A 不可重複收藏兩次 `2330`

## 7. 暫不導入 migration framework 的原因

目前先不導入完整 migration framework，原因如下：

1. 專案目前仍以 SQLite + 單機展示為主
2. 這一輪重點是明確規格與最小資料邊界，不是全面資料庫工程化
3. 若此時直接導入 Alembic / schema versioning，會讓本輪範圍膨脹

因此本階段暫時策略是：

1. 由 `init_database()` 或同層初始化流程負責最小 schema 檢查
2. 在偵測到舊表結構時，做受控的重建 / 搬移
3. 所有規則先以本文件為準

這不代表專案已具備正式 migration 能力，只代表：

1. 已有明確升級規格
2. 已有可接受的最小實作方向

## 8. 下一輪實作時應遵守的檢查點

資料隔離最小版開發時，至少應確認：

1. 空資料庫可直接啟動並建立新 schema
2. 已有舊 `watchlist` 但無 `user_id` 的資料庫可成功升級
3. 已有舊 `trades` 但無 `user_id` 的資料庫可成功升級
4. 升級後：
   - `watchlist` 舊資料已落到預期使用者
   - `trades` 舊資料已落到預期使用者
5. 新建立的收藏、BUY、SELL 都會正確保存 `user_id`
6. `portfolio`、已實現 / 未實現損益只計算目前登入使用者資料

## 9. 驗收建議情境

驗收 thread 可依以下情境檢查：

### 情境 A：空資料庫

1. 刪除既有 SQLite 檔
2. 啟動專案
3. 註冊一個新帳號
4. 新增收藏、建立 BUY / SELL
5. 確認所有功能正常

預期：

1. 不需要手動 migration
2. 直接建立含 `user_id` 的新 schema

### 情境 B：舊資料庫 + 已有使用者

1. 準備一份舊版 SQLite
2. 舊版內含 `watchlist` / `trades` 資料
3. `users` 表已有至少一位使用者
4. 啟動升級流程

預期：

1. 舊收藏與舊交易會被搬到 `users.id` 最小者
2. 升級後頁面與 service 可正常讀取

### 情境 C：兩位使用者登入後隔離檢查

1. 使用者 A 建立收藏與交易
2. 使用者 B 登入

預期：

1. B 看不到 A 的 `watchlist`
2. B 看不到 A 的 `trades`
3. B 的 `portfolio` 不會混入 A 的資料

### 情境 D：異常舊資料

1. 舊 `watchlist` / `trades` 有資料
2. `users` 為空

預期：

1. 系統不應假裝已完成正確歸戶
2. 驗收應明確標示為需人工處理的 legacy 例外情境

## 10. 結論

這份 migration 規格的核心是：

1. 下一輪資料隔離不應只改 service 查詢，必須同步處理 schema 升級
2. `watchlist` 與 `trades` 的 `user_id` 導入要有明確舊資料歸戶規則
3. 在沒有完整 migration framework 的前提下，專案仍可採「初始化時最小重建 / 搬移」策略
4. 驗收時必須同時檢查：
   - 空資料庫
   - 舊資料庫
   - 多使用者隔離
   - 異常 legacy 資料情境
