from dataclasses import dataclass


@dataclass
class AccountBalance:
    """帳戶餘額資訊 DTO"""
    asset: str  # 資產名稱
    wallet_balance: float  # 錢包餘額
    unrealized_profit: float  # 未實現盈虧
    margin_balance: float  # 保證金餘額
    maint_margin: float  # 維持保證金
    initial_margin: float  # 起始保證金
    position_initial_margin: float  # 持倉起始保證金
    open_order_initial_margin: float  # 掛單起始保證金
    max_withdraw_amount: float  # 最大可轉出餘額
    cross_wallet_balance: float  # 全倉錢包餘額
    cross_un_pnl: float  # 全倉持倉未實現盈虧
    available_balance: float  # 可用餘額

    @classmethod
    def from_api_response(cls, data: dict) -> 'AccountBalance':
        """從 API 回應建立 DTO"""
        return cls(
            asset=data['asset'],
            wallet_balance=float(data['walletBalance']),
            unrealized_profit=float(data['unrealizedProfit']),
            margin_balance=float(data['marginBalance']),
            maint_margin=float(data['maintMargin']),
            initial_margin=float(data['initialMargin']),
            position_initial_margin=float(data['positionInitialMargin']),
            open_order_initial_margin=float(data['openOrderInitialMargin']),
            max_withdraw_amount=float(data['maxWithdrawAmount']),
            cross_wallet_balance=float(data['crossWalletBalance']),
            cross_un_pnl=float(data['crossUnPnl']),
            available_balance=float(data['availableBalance'])
        )
