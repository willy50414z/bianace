from dataclasses import dataclass
from decimal import Decimal


@dataclass
class HedgeTradePriceAmt:
    price: int
    buy_amt: Decimal
    sellAmt: Decimal
