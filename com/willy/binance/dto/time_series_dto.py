from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class TimeSeriesDto:
    date: datetime
    value: Any
