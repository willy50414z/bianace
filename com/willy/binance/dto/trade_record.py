from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from com.willy.binance.enum.trade_type import TradeType


@dataclass
class TradeRecord:
    date: datetime  # 交易日期
    type: TradeType  # BUY | SELL
    price: Decimal  # 交易價格
    unit: Decimal  # 交易單位
    amt: Decimal  # 交易金額(槓桿放大後)
