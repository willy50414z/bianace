import math
from decimal import Decimal, ROUND_FLOOR
from typing import List

from com.willy.binance.config.config_util import config_util
from com.willy.binance.dto.trade_record import TradeRecord
from com.willy.binance.enum.handle_fee_type import HandleFeeType
from com.willy.binance.enum.trade_type import TradeType


def calc_buyable_units(invest_amt: Decimal, price_per_btc: Decimal, handle_fee_ratio: Decimal = Decimal(
    config_util("binance.trade.handle.fee").get(HandleFeeType.TAKER.name))) -> Decimal:
    """
    計算在手續費以 BTC 計算、投資金額以法幣計，且成交價固定時，
    無條件捨去到小數點第 3 位的可購買 BTC 數量。

    Parameters:
        invest_amt (Decimal): 總投資金額（法幣，單位元）
        price_per_btc (Decimal): BTC 價格，單位元/BTC
        handle_fee_ratio (Decimal): 手續費，以 BTC 為單位

    Returns:
        Decimal: 無條件捨去到小數點第 3 位的 BTC 數量
    """
    # 手續費換算成法幣
    fee_in_currency = handle_fee_ratio * price_per_btc
    usable_money = invest_amt - fee_in_currency
    if usable_money <= Decimal("0"):
        return Decimal("0")
    btc = usable_money / price_per_btc
    # 無條件捨去到小數點第3位
    btc_floor = btc.quantize(Decimal("0.001"), rounding=ROUND_FLOOR)
    return btc_floor


def calc_trade_amt(price: Decimal, units: Decimal, handle_fee: Decimal = Decimal(
    config_util("binance.trade.handle.fee").get(HandleFeeType.TAKER.name))) -> Decimal:
    return price * units * (1 + handle_fee)


def create_trade_record(trade_type: TradeType, price: Decimal, amt: Decimal,
                        handle_fee_type: HandleFeeType = HandleFeeType.TAKER) -> TradeRecord:
    handle_fee = Decimal(config_util("binance.trade.handle.fee").get(handle_fee_type.name))
    buyable_units = calc_buyable_units(amt, price, handle_fee)
    return TradeRecord(trade_type, price, buyable_units, calc_trade_amt(price, buyable_units, handle_fee))


def log_trade_info(trade_record_list: List[TradeRecord]):
    profit = Decimal(0)

    # for trade_record in trade_record_list:
