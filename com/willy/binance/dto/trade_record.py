from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from com.willy.binance.enums.handle_fee_type import HandleFeeType
from com.willy.binance.enums.trade_type import TradeType


@dataclass
class TradeRecord:
    date: datetime  # 交易日期
    type: TradeType  # BUY | SELL
    price: Decimal  # 交易價格
    unit: Decimal  # 交易單位
    handle_fee_type: HandleFeeType  # 手續費類別
    reason: str
