import unittest

from fastapi.testclient import TestClient

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


if __name__ == "__main__":
    unittest.main()
