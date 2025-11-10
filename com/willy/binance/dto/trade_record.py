from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from com.willy.binance.enums.trade_type import TradeType


@dataclass
class TradeRecord:
    date: datetime  # 交易日期
    type: TradeType  # BUY | SELL
    price: Decimal  # 交易價格
    unit: Decimal  # 交易單位
    handle_amt: Decimal  # 持有金額(不含手續費)
    handling_fee: Decimal  # 手續費
