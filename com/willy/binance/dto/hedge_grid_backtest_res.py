from dataclasses import dataclass
from typing import List

from com.willy.binance.dto.trade_detail import TradeDetail
from com.willy.binance.dto.txn_detail import TxnDetail


@dataclass
class HedgeGridBacktestRes:
    name: str
    trade_detail_long: TradeDetail
    trade_detail_short: TradeDetail
