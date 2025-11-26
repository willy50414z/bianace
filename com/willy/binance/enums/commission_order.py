from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class CommissionOrder:
    """委託單資訊 DTO"""
    symbol: str  # 交易對
    order_id: int  # 訂單ID
    client_order_id: str  # 客戶端訂單ID
    price: float  # 委託價格
    orig_qty: float  # 原始委託數量
    executed_qty: float  # 已成交數量
    cumulative_quote_qty: float  # 成交金額
    status: str  # 訂單狀態
    time_in_force: str  # 有效方式
    order_type: str  # 訂單類型
    side: str  # 買賣方向（BUY/SELL）
    stop_price: float  # 觸發價
    working_type: str  # 條件價格觸發類型
    activate_price: Optional[float]  # 追蹤止損激活價格
    price_rate: Optional[float]  # 追蹤止損回調比例
    update_time: datetime  # 更新時間
    position_side: str  # 持倉方向
    close_position: bool  # 是否條件全平倉

    @property
    def side_zh(self) -> str:
        """返回中文方向"""
        return "買入" if self.side == 'BUY' else "賣出"

    @property
    def remaining_qty(self) -> float:
        """返回未成交數量"""
        return self.orig_qty - self.executed_qty

    @classmethod
    def from_api_response(cls, data: dict) -> 'OrderInfo':
        """從 API 回應建立 DTO"""
        return cls(
            symbol=data['symbol'],
            order_id=int(data['orderId']),
            client_order_id=data['clientOrderId'],
            price=float(data['price']),
            orig_qty=float(data['origQty']),
            executed_qty=float(data['executedQty']),
            cumulative_quote_qty=float(data['cumQuote']),
            status=data['status'],
            time_in_force=data['timeInForce'],
            order_type=data['type'],
            side=data['side'],
            stop_price=float(data['stopPrice']),
            working_type=data['workingType'],
            activate_price=float(data['activatePrice']) if data.get('activatePrice') else None,
            price_rate=float(data['priceRate']) if data.get('priceRate') else None,
            update_time=datetime.fromtimestamp(data['updateTime'] / 1000),
            position_side=data['positionSide'],
            close_position=data['closePosition']
        )
