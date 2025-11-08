from dataclasses import dataclass
from decimal import Decimal

from com.willy.binance.dto.trade_plan import TradePlan


@dataclass
class FixedPriceInvestAmtDto(TradePlan):
    price: Decimal
    amt: Decimal
