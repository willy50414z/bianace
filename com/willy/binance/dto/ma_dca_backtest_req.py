from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from com.willy.binance.enums.binance_product import BinanceProduct


@dataclass
class MaDcaBacktestReq:
    name: str
    binance_product: BinanceProduct
    start_time: datetime
    end_time: datetime
    invest_amt: Decimal
    guarantee_amt: Decimal
    dca_levels: Decimal
    level_amt_change: Decimal  # 每網格，投資金額調整多少1.5表示每一網格投資金額*150%
    leverage_ratio: Decimal
