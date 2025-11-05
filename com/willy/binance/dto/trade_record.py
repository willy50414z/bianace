from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from com.willy.binance.enum.trade_type import TradeType


@dataclass
class TradeRecord:
    date: datetime
    type: TradeType
    price: Decimal
    unit: Decimal
    amt: Decimal
