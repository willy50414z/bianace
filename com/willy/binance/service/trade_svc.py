import math
from datetime import datetime
from decimal import Decimal, ROUND_FLOOR, ROUND_CEILING
from typing import List

from com.willy.binance.config.config_util import config_util
from com.willy.binance.config.const import DECIMAL_PLACE_2
from com.willy.binance.dto.binance_kline import BinanceKline
from com.willy.binance.dto.trade_detail import TradeDetail
from com.willy.binance.dto.trade_record import TradeRecord
from com.willy.binance.enum.handle_fee_type import HandleFeeType
from com.willy.binance.enum.trade_type import TradeType


def calc_max_loss(highest_price: Decimal, lowest_price: Decimal, total_handle_amt: Decimal, total_handle_fee,
                  units: Decimal,
                  handle_fee_type=HandleFeeType.TAKER):
    if units > 0:
        return min(calc_profit(highest_price, total_handle_amt, total_handle_fee, units, handle_fee_type),
                   calc_profit(lowest_price, total_handle_amt, total_handle_fee, units, handle_fee_type))
    else:
        return Decimal(0)


def calc_profit(current_price: Decimal, total_handle_amt: Decimal, total_handle_fee, units: Decimal,
                handle_fee_type=HandleFeeType.TAKER):
    fee_rate = Decimal(config_util("binance.trade.handle.fee").get(handle_fee_type.name))
    if units > 0:
        # 平倉多倉
        # (賣金 - 賣手續) - 買金 - 買手續
        profit = current_price * units * (1 - fee_rate) - total_handle_amt - total_handle_fee
        # profit + total_handling_amt + total_handling_fee  / units / (1 - fee_rate)
    elif units < 0:
        # 平倉空倉
        # 賣金 - 賣手續 - (買價 + 買手續)
        profit = (total_handle_amt - total_handle_fee) - current_price * -1 * units * (1 + fee_rate)
        # (total_handling_amt - total_handling_fee)- profit / -1 / units / (1 + fee_rate)
    else:
        return None
    return profit.quantize(DECIMAL_PLACE_2, ROUND_FLOOR)


def calc_force_close_offset_price(profit: Decimal, total_handle_amt: Decimal, total_handle_fee: Decimal, units: Decimal,
                                  handle_fee_type: HandleFeeType = HandleFeeType.TAKER):
    """
    Args:
        profit: 預期獲利
        total_handle_amt: 持倉金額
        total_handle_fee: 總手續費
        units: 持倉單位數
        handle_fee_type: 手續費類別

    Returns:

    """
    handle_fee_ratio = Decimal(config_util("binance.trade.handle.fee").get(handle_fee_type.name))
    if units > 0:
        force_close_offset_price = (profit + total_handle_amt + total_handle_fee) / units / (1 - handle_fee_ratio)
    elif units < 0:
        force_close_offset_price = ((total_handle_amt - total_handle_fee) - profit) / -1 / units / (
                1 + handle_fee_ratio)
    else:
        return None
    return force_close_offset_price.quantize(Decimal("1"), rounding=ROUND_CEILING)


def calc_buyable_units(invest_amt: Decimal, price: Decimal) -> Decimal:
    """

    Args:
        invest_amt: 投資額
        price: 價格
        handle_fee_type: 手續費類別

    Returns:

    """
    if invest_amt <= Decimal("0"):
        return Decimal("0")
    return (invest_amt / price).quantize(Decimal("0.001"), rounding=ROUND_FLOOR)


def calc_handle_fee(price: Decimal, units: Decimal, handle_fee_type: HandleFeeType = HandleFeeType.TAKER
                    ) -> Decimal:
    handle_fee_ratio = Decimal(config_util("binance.trade.handle.fee").get(handle_fee_type.name))
    return (price * units * handle_fee_ratio).quantize(DECIMAL_PLACE_2, rounding=ROUND_CEILING)


def create_trade_record(date: datetime, trade_type: TradeType, price: Decimal, amt: Decimal,
                        handle_fee_type: HandleFeeType = HandleFeeType.TAKER) -> TradeRecord | None:
    buyable_units = calc_buyable_units(amt, price)
    if buyable_units > 0:
        return TradeRecord(date, trade_type, price, buyable_units, price * buyable_units,
                           calc_handle_fee(price, buyable_units, handle_fee_type))
    else:
        return None


def build_trade_detail_list(binanceKline: BinanceKline, invest_amt: Decimal,
                            leverage_ratio: Decimal,
                            trade_record: TradeRecord | None, trade_detail_list=List[TradeDetail]):
    """

    Args:
        trade_detail_list:
        current_price:
        invest_amt: 投資金額(未被槓桿放大)
        leverage_ratio: 槓桿倍數
        trade_record: 新的一筆交易

    Returns:

    """
    current_price = binanceKline.close
    current_date = binanceKline.end_time
    total_handle_units = Decimal(0)
    total_handle_amt = Decimal(0)
    total_handle_fee = Decimal(0)
    last_trade_detail_guarantee = Decimal(0)
    last_trade_detail_force_close_offset_price = Decimal(0)
    last_trade_detail_acct_balance = invest_amt
    last_trade_break_even_point_price = Decimal(0)
    last_trade_max_loss = Decimal(0)
    if len(trade_detail_list) > 0:
        last_trade_detail = trade_detail_list[len(trade_detail_list) - 1]
        total_handle_units = last_trade_detail.units
        total_handle_amt = last_trade_detail.handle_amt
        total_handle_fee = last_trade_detail.handling_fee
        last_trade_detail_guarantee = last_trade_detail.guarantee_fee
        last_trade_detail_force_close_offset_price = last_trade_detail.force_force_close_offset_price
        last_trade_detail_acct_balance = last_trade_detail.acct_balance
        last_trade_break_even_point_price = last_trade_detail.break_even_point_price
        last_trade_max_loss = last_trade_detail.max_loss

    if trade_record:
        total_handle_amt += trade_record.handle_amt
        total_handle_fee += trade_record.handling_fee
        guarantee = (total_handle_amt / leverage_ratio).quantize(DECIMAL_PLACE_2, rounding=ROUND_CEILING)
        acct_balance = invest_amt - guarantee - total_handle_fee
        max_loss = calc_max_loss(binanceKline.high, binanceKline.low, total_handle_amt, total_handle_fee,
                                 total_handle_units,
                                 HandleFeeType.TAKER)

        if trade_record.type == TradeType.BUY:
            total_handle_units += trade_record.unit
            profit = calc_profit(current_price, total_handle_amt, total_handle_fee, total_handle_units,
                                 HandleFeeType.TAKER)

            force_close_offset_price = calc_force_close_offset_price(-1 * invest_amt,
                                                                     total_handle_amt, total_handle_fee,
                                                                     total_handle_units)
            break_even_point_price = calc_force_close_offset_price(Decimal(0),
                                                                   total_handle_amt, total_handle_fee,
                                                                   total_handle_units)
            trade_detail_list.append(
                TradeDetail(current_date, total_handle_units, total_handle_amt, total_handle_fee,
                            guarantee,
                            current_price, profit, force_close_offset_price, break_even_point_price, max_loss,
                            acct_balance,
                            trade_record))
        elif trade_record.type == TradeType.SELL:
            total_handle_units -= trade_record.unit
            profit = calc_profit(current_price, total_handle_amt, total_handle_fee, total_handle_units,
                                 HandleFeeType.TAKER)
            force_close_offset_price = calc_force_close_offset_price(-1 * invest_amt, total_handle_amt,
                                                                     total_handle_fee,
                                                                     total_handle_units,
                                                                     HandleFeeType.TAKER)
            break_even_point_price = calc_force_close_offset_price(Decimal(0),
                                                                   total_handle_amt, total_handle_fee,
                                                                   total_handle_units)
            trade_detail_list.append(
                TradeDetail(current_date, total_handle_units, total_handle_amt, total_handle_fee,
                            guarantee,
                            current_price, profit, force_close_offset_price, break_even_point_price, max_loss,
                            acct_balance,
                            trade_record))
    else:
        profit = calc_profit(current_price, total_handle_amt, total_handle_fee, total_handle_units,
                             HandleFeeType.TAKER)
        trade_detail_list.append(
            TradeDetail(current_date, total_handle_units, total_handle_amt, total_handle_fee,
                        last_trade_detail_guarantee,
                        current_price, profit, last_trade_detail_force_close_offset_price,
                        last_trade_break_even_point_price, last_trade_max_loss, last_trade_detail_acct_balance,
                        trade_record))

    return trade_detail_list
