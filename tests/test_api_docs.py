import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.api_errors import build_validation_issues
from app.main import app


class ApiDocsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.client.close()

    def test_swagger_ui_is_available(self) -> None:
        response = self.client.get("/docs")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Swagger UI", response.text)

    def test_openapi_schema_contains_main_tags_and_paths(self) -> None:
        response = self.client.get("/openapi.json")

        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertEqual(payload["info"]["title"], app.title)
        self.assertIn("/health", payload["paths"])
        self.assertIn("/stocks/search", payload["paths"])
        self.assertIn("/api/stocks/{stock_no}", payload["paths"])
        self.assertIn("/api/watchlist/items", payload["paths"])
        self.assertIn("/api/trades/history", payload["paths"])
        self.assertIn("/api/portfolio/summary", payload["paths"])

        tag_names = {tag["name"] for tag in payload["tags"]}
        self.assertIn("Pages", tag_names)
        self.assertIn("Stock Pages", tag_names)
        self.assertIn("Watchlist Pages", tag_names)
        self.assertIn("Trade Pages", tag_names)
        self.assertIn("Stocks API", tag_names)
        self.assertIn("Watchlist API", tag_names)
        self.assertIn("Trading API", tag_names)
        self.assertIn("Portfolio API", tag_names)
        self.assertIn("System", tag_names)

        stock_api = payload["paths"]["/api/stocks/{stock_no}"]["get"]
        self.assertEqual(stock_api["summary"], "查詢單一台股歷史資料")
        self.assertIn("JSON", stock_api["description"])
        self.assertIn("400", stock_api["responses"])
        self.assertIn("404", stock_api["responses"])
        self.assertIn("422", stock_api["responses"])
        self.assertIn("502", stock_api["responses"])
        self.assertEqual(
            stock_api["responses"]["400"]["content"]["application/json"]["schema"]["$ref"],
            "#/components/schemas/ApiErrorResponse",
        )

    def test_api_error_schema_for_invalid_stock_input(self) -> None:
        response = self.client.get(
            "/api/stocks/abcd",
            params={"start_date": "2024-05-01", "end_date": "2024-05-31"},
        )

        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertEqual(payload["error_code"], "INVALID_INPUT")
        self.assertIn("股票代號格式錯誤", payload["message"])
        self.assertEqual(payload["validation_errors"], [])

    def test_api_error_schema_for_missing_required_query(self) -> None:
        response = self.client.get("/api/stocks/2330", params={"start_date": "2024-05-01"})

        self.assertEqual(response.status_code, 422)
        payload = response.json()
        self.assertEqual(payload["error_code"], "VALIDATION_ERROR")
        self.assertEqual(payload["message"], "API 請求參數驗證失敗，請確認必填欄位與格式。")
        self.assertTrue(payload["validation_errors"])
        self.assertEqual(payload["validation_errors"][0]["field"], "end_date")
        self.assertEqual(payload["validation_errors"][0]["message"], "缺少必要欄位。")

    def test_validation_issue_messages_are_translated_to_traditional_chinese(self) -> None:
        issues = build_validation_issues(
            [
                {"type": "missing", "loc": ("query", "end_date"), "msg": "Field required"},
                {"type": "int_parsing", "loc": ("query", "limit"), "msg": "Input should be a valid integer"},
                {
                    "type": "date_parsing",
                    "loc": ("query", "start_date"),
                    "msg": "Input should be a valid date or datetime, input is too short",
                },
                {"type": "unknown_error", "loc": ("query", "keyword"), "msg": "Something unexpected"},
            ]
        )

        self.assertEqual(issues[0].field, "end_date")
        self.assertEqual(issues[0].message, "缺少必要欄位。")
        self.assertEqual(issues[1].message, "limit 格式錯誤，請輸入整數。")
        self.assertEqual(issues[2].message, "日期格式錯誤，請使用 YYYY-MM-DD。")
        self.assertEqual(issues[3].message, "查詢參數格式錯誤。")

    @patch("app.routers.api.fetch_stock_detail")
    def test_api_error_schema_for_external_service_failure(self, mock_fetch) -> None:
        from app.services.stock_service import ExternalServiceError

        mock_fetch.side_effect = ExternalServiceError("股票資料來源暫時無法使用，請稍後再試。")

        response = self.client.get(
            "/api/stocks/2330",
            params={"start_date": "2024-05-01", "end_date": "2024-05-31"},
        )

        self.assertEqual(response.status_code, 502)
        self.assertEqual(
            response.json(),
            {
                "error_code": "EXTERNAL_SERVICE_ERROR",
                "message": "股票資料來源暫時無法使用，請稍後再試。",
                "validation_errors": [],
            },
        )


if __name__ == "__main__":
    unittest.main()
