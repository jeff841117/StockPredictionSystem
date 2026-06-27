import logging
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.error_monitoring import record_error_event


class ErrorMonitoringTests(unittest.TestCase):
    def test_record_error_event_writes_json_log_line(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "app-errors.log"

            with patch("app.error_monitoring.settings.error_log_path", str(log_path)):
                logger = logging.getLogger("stock_prediction_system.errors")
                for handler in logger.handlers:
                    handler.close()
                logger.handlers.clear()
                record_error_event(
                    flow="api",
                    category="external_service_error",
                    route="/api/stocks/2330",
                    user_message="股票資料來源暫時無法使用，請稍後再試。",
                    internal_message="ExternalServiceError('twse timeout')",
                    status_code=502,
                )
                for handler in logger.handlers:
                    handler.flush()
                    handler.close()
                logger.handlers.clear()

            self.assertTrue(log_path.exists())
            lines = log_path.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 1)

            payload = json.loads(lines[0])
            self.assertEqual(payload["event"], "application_error")
            self.assertEqual(payload["flow"], "api")
            self.assertEqual(payload["category"], "external_service_error")
            self.assertEqual(payload["route"], "/api/stocks/2330")
            self.assertEqual(payload["status_code"], 502)
            self.assertEqual(payload["user_message"], "股票資料來源暫時無法使用，請稍後再試。")
            self.assertEqual(payload["internal_message"], "ExternalServiceError('twse timeout')")
            self.assertIn("timestamp", payload)


if __name__ == "__main__":
    unittest.main()
