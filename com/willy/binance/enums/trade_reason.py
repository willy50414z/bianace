from dataclasses import dataclass
from enum import Enum


class TradeReasonType(Enum):
    ACTIVE = 1
    PASSIVE = 2


@dataclass
class TradeReason:
    trade_reason_type: TradeReasonType
    desc: str
