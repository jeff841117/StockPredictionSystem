import os
import re
import unittest
from datetime import date

from app.services.stock_service import ExternalServiceError, get_latest_close_price


PRICE_PATTERN = re.compile(r"^\d+(?:\.\d{2})$")


@unittest.skipUnless(
    os.getenv("RUN_TWSE_SMOKE") == "1",
    "真實 TWSE smoke test 預設跳過。執行前請設定 RUN_TWSE_SMOKE=1。",
)
class TwseLatestPriceSmokeTests(unittest.TestCase):
    def test_get_latest_close_price_real_twse_path(self) -> None:
        stock_no = "2330"
        today = date.today()
        next_month_reference = _get_next_month_start(today)

        try:
            direct_price = get_latest_close_price(stock_no, months_to_check=3, reference_date=today)
            backfilled_price = get_latest_close_price(stock_no, months_to_check=3, reference_date=next_month_reference)
        except ExternalServiceError as exc:
            self.fail(f"EXTERNAL_DATA_ERROR: TWSE 真實價格路徑無法使用，請稍後再試。詳細原因：{exc}")
        except Exception as exc:  # pragma: no cover - smoke test diagnostic path
            self.fail(f"LOGIC_ERROR: 真實價格路徑執行發生未預期例外。詳細原因：{exc}")

        if direct_price is None:
            self.fail("EXTERNAL_DATA_STATE: 目前日期附近無法取得 2330 的最近收盤價，無法完成 smoke test。")
        if backfilled_price is None:
            self.fail("EXTERNAL_DATA_STATE: 回補查找流程未取得最近收盤價，可能是外部資料暫時不可得。")

        self.assertRegex(direct_price, PRICE_PATTERN)
        self.assertRegex(backfilled_price, PRICE_PATTERN)
        self.assertEqual(
            direct_price,
            backfilled_price,
            "LOGIC_ERROR: 向前回補查找結果與直接查找結果不一致，請檢查最近價格回補邏輯。",
        )


def _get_next_month_start(base_date: date) -> date:
    month_start = base_date.replace(day=1)
    if month_start.month == 12:
        return date(month_start.year + 1, 1, 1)
    return date(month_start.year, month_start.month + 1, 1)


if __name__ == "__main__":
    unittest.main()
