from dataclasses import dataclass
from typing import List

from com.willy.binance.dto.trade_detail import TradeDetail


@dataclass
class HedgeGridBacktestRes:
    name: str
    trade_detail_long_list: List[TradeDetail]
    trade_detail_short_list: List[TradeDetail]
