from dataclasses import dataclass
from typing import List

from com.willy.binance.dto.acct_balance import AccountBalance
from com.willy.binance.dto.position_info import PositionInfo


@dataclass
class FuturesAccountInfo:
    """合約帳戶完整資訊 DTO"""
    total_wallet_balance: float  # 總錢包餘額
    total_unrealized_profit: float  # 總未實現盈虧
    total_margin_balance: float  # 總保證金餘額
    total_position_initial_margin: float  # 總持倉起始保證金
    total_open_order_initial_margin: float  # 總掛單起始保證金
    total_cross_wallet_balance: float  # 全倉錢包餘額
    total_cross_un_pnl: float  # 全倉持倉未實現盈虧
    available_balance: float  # 可用餘額
    max_withdraw_amount: float  # 最大可轉出餘額
    assets: List[AccountBalance]  # 各資產餘額
    positions: List[PositionInfo]  # 持倉列表

    @classmethod
    def from_api_response(cls, data: dict) -> 'FuturesAccountInfo':
        """從 API 回應建立 DTO"""
        return cls(
            total_wallet_balance=float(data['totalWalletBalance']),
            total_unrealized_profit=float(data['totalUnrealizedProfit']),
            total_margin_balance=float(data['totalMarginBalance']),
            total_position_initial_margin=float(data['totalPositionInitialMargin']),
            total_open_order_initial_margin=float(data['totalOpenOrderInitialMargin']),
            total_cross_wallet_balance=float(data['totalCrossWalletBalance']),
            total_cross_un_pnl=float(data['totalCrossUnPnl']),
            available_balance=float(data['availableBalance']),
            max_withdraw_amount=float(data['maxWithdrawAmount']),
            assets=[AccountBalance.from_api_response(asset) for asset in data['assets']],
            positions=[PositionInfo.from_api_response(pos) for pos in data['positions']
                       if float(pos['positionAmt']) != 0]
        )
