from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from com.willy.binance.dto.trade_record import TradeRecord
from com.willy.binance.enums.trade_type import TradeType


@dataclass
class TxnDetail:
    date: datetime
    units: Decimal
    handle_amt: Decimal
    handling_fee: Decimal
    guarantee_fee: Decimal
    current_price: Decimal
    profit: Decimal
    profit_ratio: Decimal
    force_close_offset_price: Decimal
    break_even_point_price: Decimal
    max_loss: Decimal
    acct_balance: Decimal
    trade_record: TradeRecord
