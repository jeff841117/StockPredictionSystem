from pydantic import BaseModel, Field


class ApiValidationIssue(BaseModel):
    field: str = Field(description="驗證失敗的欄位位置，例如 `body.stock_name`。")
    message: str = Field(description="已轉為繁體中文的驗證錯誤訊息。")

    model_config = {
        "json_schema_extra": {
            "example": {
                "field": "body.stock_name",
                "message": "缺少必要欄位。",
            }
        }
    }


class ApiErrorResponse(BaseModel):
    error_code: str = Field(description="固定錯誤代碼，用於區分錯誤類型。")
    message: str = Field(description="給 API 使用者閱讀的錯誤訊息。")
    validation_errors: list[ApiValidationIssue] = Field(
        default_factory=list,
        description="輸入驗證錯誤明細；非驗證錯誤時為空陣列。",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "error_code": "INVALID_INPUT",
                "message": "股票代號格式錯誤，請輸入 4 位數台股代號。",
                "validation_errors": [],
            }
        }
    }


class HealthCheckResponse(BaseModel):
    status: str = Field(description="系統狀態字串，正常時為 `ok`。")

    model_config = {"json_schema_extra": {"example": {"status": "ok"}}}


class WatchlistItemResponse(BaseModel):
    stock_no: str = Field(description="台股代號。")
    stock_name: str = Field(description="股票名稱。")
    created_at: str = Field(description="加入收藏時間，格式為 `YYYY-MM-DD HH:MM:SS`。")

    model_config = {
        "json_schema_extra": {
            "example": {
                "stock_no": "2330",
                "stock_name": "台積電",
                "created_at": "2024-05-31 10:00:00",
            }
        }
    }


class WatchlistCreateRequest(BaseModel):
    stock_no: str = Field(description="台股代號。")
    stock_name: str = Field(description="股票名稱。")

    model_config = {
        "json_schema_extra": {
            "example": {
                "stock_no": "2330",
                "stock_name": "台積電",
            }
        }
    }


class ApiMessageResponse(BaseModel):
    message: str = Field(description="簡短操作結果訊息。")

    model_config = {"json_schema_extra": {"example": {"message": "已成功移除收藏股票。"}}}


class AuditLogResponse(BaseModel):
    event_type: str = Field(description="操作事件類型，例如 `AUTH_LOGIN`。")
    username: str = Field(description="觸發事件的使用者帳號。")
    created_at: str = Field(description="事件發生時間，格式為 `YYYY-MM-DD HH:MM:SS`。")
    target_type: str = Field(description="目標資源類型，例如 `stock`、`session`、`user`。")
    target_value: str = Field(description="目標資源值，例如股票代號或頁面路徑。")
    status: str = Field(description="事件結果狀態，目前最小版主要為 `success`。")
    context: str = Field(description="最小上下文資訊，使用 JSON 字串保存。")

    model_config = {
        "json_schema_extra": {
            "example": {
                "event_type": "TRADE_BUY",
                "username": "demo_user",
                "created_at": "2024-05-31 09:00:00",
                "target_type": "stock",
                "target_value": "2330",
                "status": "success",
                "context": "{\"price\": \"800.00\", \"quantity\": 100, \"stock_name\": \"台積電\", \"trade_time\": \"2024-05-31 09:00:00\"}",
            }
        }
    }


class TradeRecordResponse(BaseModel):
    id: int = Field(description="交易紀錄主鍵。")
    stock_no: str = Field(description="台股代號。")
    stock_name: str = Field(description="股票名稱。")
    trade_type: str = Field(description="交易類型，目前為 `BUY` 或 `SELL`。")
    price: str = Field(description="交易價格，已格式化為字串。")
    quantity: int = Field(description="交易股數。")
    trade_time: str = Field(description="交易時間，格式為 `YYYY-MM-DD HH:MM:SS`。")
    total_amount: str = Field(description="交易總金額，已格式化為字串。")
    realized_pnl: str = Field(description="SELL 交易的已實現損益；BUY 時為 `-`。")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": 12,
                "stock_no": "2330",
                "stock_name": "台積電",
                "trade_type": "SELL",
                "price": "900.00",
                "quantity": 40,
                "trade_time": "2024-06-01 09:00:00",
                "total_amount": "36,000.00",
                "realized_pnl": "4,000.00",
            }
        }
    }


class VirtualCashSummaryResponse(BaseModel):
    initial_cash: str = Field(description="初始虛擬資金。")
    used_cash: str = Field(description="目前已使用資金。")
    available_cash: str = Field(description="目前可用資金。")

    model_config = {
        "json_schema_extra": {
            "example": {
                "initial_cash": "1,000,000.00",
                "used_cash": "44,000.00",
                "available_cash": "956,000.00",
            }
        }
    }


class PositionSummaryResponse(BaseModel):
    stock_no: str = Field(description="台股代號。")
    stock_name: str = Field(description="股票名稱。")
    quantity: int = Field(description="目前持股數量。")
    average_cost: str = Field(description="目前持股的加權平均成本。")
    total_buy_amount: str = Field(description="目前持股成本基礎。")
    current_price: str = Field(description="最近可取得收盤價；缺價時為 `-`。")
    market_value: str = Field(description="估算市值；缺價時為 `-`。")
    unrealized_pnl: str = Field(description="未實現損益；缺價時為 `-`。")
    price_note: str = Field(description="價格缺失或格式異常時的補充說明。")

    model_config = {
        "json_schema_extra": {
            "example": {
                "stock_no": "2330",
                "stock_name": "台積電",
                "quantity": 60,
                "average_cost": "800.00",
                "total_buy_amount": "48,000.00",
                "current_price": "850.00",
                "market_value": "51,000.00",
                "unrealized_pnl": "3,000.00",
                "price_note": "",
            }
        }
    }


class UnrealizedPnlSummaryResponse(BaseModel):
    total_unrealized_pnl: str = Field(description="所有已成功估值持股的未實現損益總和。")
    priced_position_count: int = Field(description="已成功取得價格並完成估值的持股檔數。")
    missing_price_count: int = Field(description="暫時無法取得價格的持股檔數。")

    model_config = {
        "json_schema_extra": {
            "example": {
                "total_unrealized_pnl": "3,000.00",
                "priced_position_count": 1,
                "missing_price_count": 0,
            }
        }
    }


class PortfolioOverviewResponse(BaseModel):
    positions: list[PositionSummaryResponse] = Field(description="目前持股清單與各檔估值結果。")
    unrealized_summary: UnrealizedPnlSummaryResponse = Field(description="未實現損益摘要。")

    model_config = {
        "json_schema_extra": {
            "example": {
                "positions": [
                    {
                        "stock_no": "2330",
                        "stock_name": "台積電",
                        "quantity": 60,
                        "average_cost": "800.00",
                        "total_buy_amount": "48,000.00",
                        "current_price": "850.00",
                        "market_value": "51,000.00",
                        "unrealized_pnl": "3,000.00",
                        "price_note": "",
                    }
                ],
                "unrealized_summary": {
                    "total_unrealized_pnl": "3,000.00",
                    "priced_position_count": 1,
                    "missing_price_count": 0,
                },
            }
        }
    }


class PortfolioSummaryResponse(BaseModel):
    initial_cash: str = Field(description="初始虛擬資金。")
    available_cash: str = Field(description="目前可用資金。")
    used_cash: str = Field(description="目前已使用資金。")
    holdings_market_value: str = Field(description="目前已知持股市值總和。")
    total_realized_pnl: str = Field(description="累計已實現損益。")
    total_unrealized_pnl: str = Field(description="整體未實現損益。")
    total_asset_estimate: str = Field(description="總資產估值，計算規則為可用資金加持股市值。")
    missing_price_count: int = Field(description="暫時無法取得價格、未納入估值的持股檔數。")

    model_config = {
        "json_schema_extra": {
            "example": {
                "initial_cash": "1,000,000.00",
                "available_cash": "956,000.00",
                "used_cash": "44,000.00",
                "holdings_market_value": "51,000.00",
                "total_realized_pnl": "4,000.00",
                "total_unrealized_pnl": "3,000.00",
                "total_asset_estimate": "1,007,000.00",
                "missing_price_count": 0,
            }
        }
    }
