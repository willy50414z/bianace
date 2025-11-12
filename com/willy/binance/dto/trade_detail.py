from dataclasses import dataclass
from typing import List

from com.willy.binance.dto.txn_detail import TxnDetail


@dataclass
class TradeDetail:
    is_circuit_breaker: bool
    is_grid_break: bool
    txn_detail_list: List[TxnDetail]
