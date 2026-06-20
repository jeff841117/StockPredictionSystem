from dataclasses import dataclass


@dataclass(frozen=True)
class WatchlistItem:
    stock_no: str
    stock_name: str
    created_at: str
