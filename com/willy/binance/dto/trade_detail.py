from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from com.willy.binance.dto.trade_record import TradeRecord
from com.willy.binance.enum.trade_type import TradeType


@dataclass
class TradeDetail:
    trade_record: TradeRecord
    units: Decimal
    avg_price: Decimal
    amt: Decimal
    guarantee_fee: Decimal
    current_price: Decimal
    profit: Decimal
    force_force_close_offset_price: Decimal
    acct_balance: Decimal
