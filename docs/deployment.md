# Docker 與部署說明

本文件整理目前 `main` 主線的最小容器化與部署說明。  
定位是：

1. 支援作品集展示
2. 支援手動部署交接
3. 說明 Cloudflare 與自購網域在整體架構中的位置

不代表本專案已進入正式交易平台等級的生產化部署，也不代表 Docker 實機驗證已在目前這台開發機完成。

## 1. 目前部署定位

目前專案部署目標是：

1. 可在本機直接啟動
2. 可用 Docker 啟動 FastAPI
3. 可部署到一台 VM / VPS / 雲端主機做展示

目前不包含：

1. Kubernetes
2. PostgreSQL
3. CI/CD 自動部署
4. 多使用者權限隔離
5. 真實交易系統等級的高可用架構

## 1.1 驗證狀態

目前狀態要分開看：

1. 文件與容器檔案
   - 已提供 `Dockerfile`
   - 已提供 `docker-compose.yml`
   - 已整理 volume、環境變數與展示部署說明

2. 本機 Docker 實機驗證
   - 尚未完成
   - 原因不是專案程式錯誤，而是目前 Windows / WSL / Docker 環境阻塞

因此目前本輪應解讀為：

- `Docker / deployment 文件已完成`
- `Docker 實機驗證待有可用 Docker 環境後補做`

## 2. 本機啟動

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

預設入口：

- 首頁：`http://127.0.0.1:8000/`
- Swagger UI：`http://127.0.0.1:8000/docs`
- OpenAPI JSON：`http://127.0.0.1:8000/openapi.json`

## 3. Docker 啟動

以下指令為預期驗證與部署指令；在有可用 Docker 環境的機器上，應補做實際驗證。

### 3.1 使用 Dockerfile

```bash
docker build -t stock-prediction-system .
docker run --rm -p 8000:8000 -v ${PWD}/data:/app/data stock-prediction-system
```

說明：

1. 容器內 FastAPI 會以 `0.0.0.0:8000` 啟動
2. `data` volume 用來保留 SQLite 資料
3. 若不掛 volume，容器重建後 `watchlist` 與 `trades` 資料會遺失

### 3.2 使用 docker-compose

```bash
docker compose up --build
```

停止：

```bash
docker compose down
```

Compose 預設會：

1. 建立 FastAPI 容器
2. 開放本機 `8000 -> 容器 8000`
3. 掛載 `./data -> /app/data`
4. 以環境變數注入目前設定

## 4. 環境變數設定

專案目前支援從專案根目錄的 `.env` 讀取設定。  
容器環境中也可直接用環境變數覆蓋相同欄位。

可參考 `.env.example`：

```env
APP_NAME=台股分析與模擬交易系統
DEBUG=false
HOST=127.0.0.1
PORT=8000
STOCK_QUERY_SOURCE=https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY
STOCK_QUERY_DATE=20240501
INITIAL_VIRTUAL_CASH=1000000
WATCHLIST_DB_PATH=data/watchlist.db
```

Docker 環境建議注意：

1. `HOST` 建議為 `0.0.0.0`
2. `WATCHLIST_DB_PATH` 建議保留在 `/app/data` 對應的相對位置
3. 若要覆蓋預設值，可在執行 `docker run` 或 `docker compose` 時帶入環境變數

## 5. SQLite / data 目錄注意事項

目前專案仍使用 SQLite，因此要特別注意資料持久化：

1. `watchlist.db` 預設會落在 `data/`
2. 若容器未掛載 volume，重建容器後資料可能消失
3. `data/` 不建議直接打包進 image
4. 展示環境與本機環境若共用資料檔，需自行管理備份與覆寫風險

目前這樣的設計適合：

1. MVP 展示
2. 面試 demo
3. 小型手動部署

不適合直接視為正式多使用者平台的資料層方案。

## 6. Cloudflare 與自購網域角色

目前較適合的展示型部署架構如下：

```text
使用者瀏覽器
  -> Cloudflare DNS / Proxy / TLS
  -> 你的自購網域
  -> VM / VPS / 雲端主機
  -> Docker 容器中的 FastAPI
  -> SQLite volume（data/）
```

角色拆分：

1. Cloudflare
   - 管理 DNS
   - 提供 HTTPS / proxy
   - 隱藏來源主機 IP

2. 自購網域
   - 提供對外展示入口
   - 作為作品集與 demo 的固定網址

3. VM / VPS / 雲端主機
   - 實際執行 Docker 容器
   - 負責對外提供 FastAPI 應用

4. SQLite / `data` volume
   - 保存收藏、模擬交易與投資組合資料

## 7. 部署建議

對目前 `main` 主線，建議部署節奏如下：

1. 先在本機用 `uvicorn` 驗證
2. 再用 Docker 啟動相同應用
3. 確認 `data` volume 已正常掛載
4. 再部署到單一 VM / VPS 做展示
5. 最後把自購網域透過 Cloudflare 指到展示主機

若目前開發機沒有可用 Docker 環境，可改在以下環境補驗：

1. 另一台已安裝 Docker Desktop 的 Windows 機器
2. Linux VM / VPS
3. 雲端主機

## 8. 目前限制

1. 本輪只提供最小 Docker / deployment 展示能力
2. 目前尚未完成 `docker build`、`docker run`、`docker compose up --build` 的本機實測
3. 尚未加入 Nginx、Traefik 或正式反向代理設定
4. 尚未加入 CI/CD 與自動化部署腳本
5. 尚未把 SQLite 升級成較適合多使用者的資料庫
