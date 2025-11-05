from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass
class BinanceKline:
    start_time: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    vol: Decimal
    end_time: datetime
    number_of_trade: int
