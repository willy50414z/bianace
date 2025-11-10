from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import List

from binance import Client

from com.willy.binance.dto.trade_detail import TradeDetail
from com.willy.binance.enums.binance_product import BinanceProduct


@dataclass
class HedgeGridBacktestReq:
    name: str
    binance_product: BinanceProduct
    invest_time_interval: str
    lower_bound: int
    upper_bound: int
    grid_levels: str  # 網格劃分數量 '10'表示劃分成10格做交易
    start_time: datetime
    end_time: datetime
    invest_amt: Decimal
    level_amt_change: str  # 每網格，投資金額調整多少'150%'表示每一網格投資金額*150%
    leverage_ratio: Decimal
