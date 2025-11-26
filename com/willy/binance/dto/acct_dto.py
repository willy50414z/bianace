from dataclasses import dataclass, field
from typing import List


@dataclass
class AcctBalance:
    asset: str
    free: float
    locked: float


@dataclass
class AcctDto:
    balances: List[AcctBalance] = field(default_factory=list)
