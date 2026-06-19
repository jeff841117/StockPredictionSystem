# Commit 與 Push 流程

## 1. 文件目的

這份文件用來定義本專案的 GitHub 提交節奏。  
目標是讓每次修改都清楚、可追蹤、可展示，並讓 GitHub 紀錄對作品集有加分效果。

## 2. 核心原則

1. 盡量一個功能一個 commit / push
2. 規格、實作、驗收結果要能互相對應
3. 不把多個不相關功能混在同一次提交
4. 提交前先做最小必要驗證
5. commit 訊息要能讓人快速看懂這次做了什麼

## 3. 什麼叫做一個可提交功能

一個可提交功能通常應該符合：

1. 有明確目標
2. 有清楚邊界
3. 有對應規格
4. 有基本驗收方式
5. 修改內容彼此相關

例如：

1. 初始化 FastAPI 專案骨架
2. 新增首頁與模板基底
3. 新增股票查詢服務
4. 新增收藏清單 CRUD
5. 新增模擬買進功能

## 4. 不建議混在一起的內容

以下內容盡量不要混進同一個 commit：

1. 不同功能模組的修改
2. 功能實作和大量無關重構
3. 功能實作和大規模排版清理
4. 驗收修正和另一個全新功能

## 5. 每次提交前建議檢查

1. 這次是否只做一個功能或一個明確子功能
2. 文件是否已同步更新
3. 基本測試是否已完成
4. 是否還有明顯未完成的程式碼
5. 是否夾帶不相關修改

## 6. 建議的工作流程

每一輪可以照這個順序：

1. 先寫或更新功能規格
2. 依規格完成實作
3. 做最小必要測試
4. 更新相關文件
5. 檢查修改範圍
6. commit
7. push

## 7. commit 訊息建議格式

建議使用簡潔、可讀的格式：

1. `docs: ...`
2. `feat: ...`
3. `fix: ...`
4. `refactor: ...`
5. `test: ...`
6. `chore: ...`

## 8. 適合本專案的 commit 範例

1. `docs: add initial project specification`
2. `feat: initialize FastAPI project structure`
3. `feat: add homepage template and static assets`
4. `feat: add stock query service`
5. `feat: add stock history page and trend chart`
6. `feat: add MA5 and MA20 indicators`
7. `feat: add watchlist CRUD flow`
8. `feat: add paper trading buy flow`
9. `feat: add paper trading sell flow`
10. `feat: add portfolio summary and profit calculation`
11. `docs: add deployment and learning notes`

## 9. 什麼情況可以拆成兩個 commit

如果一個功能自然分成兩段，可以拆成兩個 commit，例如：

1. 先建結構與路由
2. 再補核心邏輯與測試

例如：

1. `feat: add watchlist routes and templates`
2. `feat: implement watchlist CRUD logic`

## 10. 什麼情況不應該急著 push

以下情況建議先不要 push：

1. 功能還沒跑通
2. 驗收標準尚未滿足
3. 修改內容混雜過多
4. 明顯有未處理錯誤
5. 還沒整理這次修改的目的

## 11. 與多 thread 協作的關係

在多 thread 流程中，commit / push 建議發生在：

1. `規劃` thread 已完成本輪規格
2. `開發` thread 已完成本輪功能
3. `驗收` thread 已完成檢查
4. 使用者確認這輪修改可以結案

## 12. 每次 push 後建議補充

建議在學習紀錄或工作紀錄中補：

1. 這次做了什麼
2. 遇到什麼問題
3. 怎麼解決
4. 下次要接哪個功能
