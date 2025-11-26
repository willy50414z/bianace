from dataclasses import dataclass


@dataclass
class PositionInfo:
    """倉位資訊 DTO"""
    symbol: str  # 交易對
    position_amt: float  # 持倉數量（正數=多單，負數=空單）
    entry_price: float  # 開倉價格
    mark_price: float  # 標記價格
    unrealized_pnl: float  # 未實現盈虧
    liquidation_price: float  # 清算價格
    leverage: int  # 槓桿倍數
    margin_type: str  # 保證金類型（isolated/cross）
    position_side: str  # 持倉方向（LONG/SHORT/BOTH）
    notional: float  # 名義價值
    isolated_wallet: float  # 逐倉錢包餘額

    @property
    def side(self) -> str:
        """返回中文方向"""
        return "多單" if self.position_amt > 0 else "空單"

    @property
    def abs_position_amt(self) -> float:
        """返回持倉絕對值"""
        return abs(self.position_amt)

    @classmethod
    def from_api_response(cls, data: dict) -> 'PositionInfo':
        """從 API 回應建立 DTO"""
        return cls(
            symbol=data['symbol'],
            position_amt=float(data['positionAmt']),
            entry_price=float(data['entryPrice']),
            mark_price=float(data['markPrice']),
            unrealized_pnl=float(data['unRealizedProfit']),
            liquidation_price=float(data['liquidationPrice']),
            leverage=int(data['leverage']),
            margin_type=data['marginType'],
            position_side=data['positionSide'],
            notional=float(data['notional']),
            isolated_wallet=float(data['isolatedWallet'])
        )
