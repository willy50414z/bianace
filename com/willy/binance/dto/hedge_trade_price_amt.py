from dataclasses import dataclass
from decimal import Decimal


@dataclass
class HedgeTradePriceAmt:
    price: Decimal
    buy_amt: Decimal
    sellAmt: Decimal
    has_trade: bool
