from dataclasses import dataclass
from decimal import Decimal

from com.willy.binance.enum.trade_type import TradeType


@dataclass
class TradeRecord:
    type: TradeType
    price: Decimal
    unit: Decimal
    amt: Decimal
