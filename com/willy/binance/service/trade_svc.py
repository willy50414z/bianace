from datetime import datetime
from decimal import Decimal, ROUND_FLOOR, ROUND_CEILING

from com.willy.binance.config.config_util import config_util
from com.willy.binance.config.const import DECIMAL_PLACE_2
from com.willy.binance.dto.binance_kline import BinanceKline
from com.willy.binance.dto.trade_detail import TradeDetail
from com.willy.binance.dto.trade_record import TradeRecord
from com.willy.binance.dto.txn_detail import TxnDetail
from com.willy.binance.enums.handle_fee_type import HandleFeeType
from com.willy.binance.enums.trade_type import TradeType


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


def calc_trade_amt(price: Decimal, units: Decimal) -> Decimal:
    return price * units


def create_trade_record(date: datetime, trade_type: TradeType, price: Decimal, amt: Decimal = None,
                        unit: Decimal = None,
                        handle_fee_type: HandleFeeType = HandleFeeType.TAKER) -> TradeRecord | None:
    if (amt and unit) or (amt is None and unit is None):
        raise ValueError("amt and unit can't both not none")
    if amt:
        buyable_units = calc_buyable_units(amt, price)
    if unit:
        buyable_units = unit

    if buyable_units > 0:
        return TradeRecord(date, trade_type, price, buyable_units, handle_fee_type)
    else:
        return None


def build_txn_detail_list_df(row, invest_amt: Decimal, guarantee_amt: Decimal,
                             leverage_ratio: Decimal,
                             trade_record: TradeRecord | None, trade_detail: TradeDetail):
    return build_txn_detail_list(
        BinanceKline(row.start_time, Decimal(row.open), Decimal(row.high), Decimal(row.low), Decimal(row.close),
                     Decimal(row.vol), row.end_time,
                     int(row.number_of_trade)), invest_amt, guarantee_amt, leverage_ratio, trade_record, trade_detail)


def build_txn_detail_list(binanceKline: BinanceKline, invest_amt: Decimal, guarantee_amt: Decimal,
                          leverage_ratio: Decimal,
                          trade_record: TradeRecord | None, trade_detail: TradeDetail):
    """

    :param binanceKline:
    :param invest_amt: 投資金額(未被槓桿放大)
    leverage_ratio: 槓桿倍數
    trade_record: 新的一筆交易
    :param trade_detail:
    :return:
    """
    current_price = binanceKline.close
    current_date = binanceKline.start_time
    last_handle_units = Decimal(0)
    last_handle_amt = Decimal(0)
    last_handle_fee = Decimal(0)
    last_trade_detail_guarantee = Decimal(0)
    last_trade_detail_force_close_offset_price = Decimal(0)
    last_trade_detail_acct_balance = invest_amt
    last_trade_break_even_point_price = Decimal(0)
    last_trade_max_loss = Decimal(0)
    last_total_profit = Decimal(0)
    if len(trade_detail.txn_detail_list) > 0:
        last_trade_detail = trade_detail.txn_detail_list[len(trade_detail.txn_detail_list) - 1]
        last_handle_units = last_trade_detail.units
        last_handle_amt = last_trade_detail.handle_amt
        last_handle_fee = last_trade_detail.handling_fee
        last_trade_detail_guarantee = last_trade_detail.guarantee_fee
        last_trade_detail_force_close_offset_price = last_trade_detail.force_close_offset_price
        last_trade_detail_acct_balance = last_trade_detail.acct_balance
        last_trade_break_even_point_price = last_trade_detail.break_even_point_price
        last_trade_max_loss = last_trade_detail.max_loss
        last_total_profit = last_trade_detail.total_profit

    if trade_record:
        if trade_record.type == TradeType.BUY:
            total_handle_units = last_handle_units + trade_record.unit
            trade_amt = calc_trade_amt(trade_record.price, trade_record.unit)
            if last_handle_units >= 0:
                total_handle_amt = last_handle_amt + trade_amt
                total_handle_fee = last_handle_fee + calc_handle_fee(trade_record.price, trade_record.unit,
                                                                     trade_record.handle_fee_type)
                profit = Decimal(0)
                profit_ratio = Decimal(0)
            else:
                # 賣轉買
                if trade_record.unit > abs(last_handle_units):
                    # 買入單位>之前持有的空倉單位
                    remain_unit = (trade_record.unit + last_handle_units)
                    total_handle_amt = calc_trade_amt(trade_record.price, remain_unit)
                    total_handle_fee = calc_handle_fee(trade_record.price, remain_unit, trade_record.handle_fee_type)
                    profit = calc_profit(trade_record.price, last_handle_amt, last_handle_fee, last_handle_units,
                                         trade_record.handle_fee_type)
                    profit_ratio = profit / last_trade_detail_guarantee
                else:
                    # 買入部分<放空艙位
                    total_handle_amt = last_handle_amt / last_handle_units * total_handle_units
                    total_handle_fee = last_handle_fee / last_handle_units * total_handle_units
                    profit = calc_profit(trade_record.price,
                                         -1 * (last_handle_amt / last_handle_units * trade_record.unit),
                                         last_handle_fee - total_handle_fee, -1 * trade_record.unit,
                                         trade_record.handle_fee_type)
                    profit_ratio = profit / ((last_handle_amt - total_handle_amt) / leverage_ratio).quantize(
                        DECIMAL_PLACE_2, rounding=ROUND_CEILING)

            guarantee = (total_handle_amt / leverage_ratio).quantize(DECIMAL_PLACE_2, rounding=ROUND_CEILING)
            acct_balance = invest_amt + guarantee_amt - guarantee - total_handle_fee
            max_loss = calc_max_loss(binanceKline.high, binanceKline.low, total_handle_amt, total_handle_fee,
                                     total_handle_units,
                                     HandleFeeType.TAKER)

            force_close_offset_price = calc_force_close_offset_price(-1 * (invest_amt + guarantee_amt),
                                                                     total_handle_amt,
                                                                     total_handle_fee,
                                                                     total_handle_units,
                                                                     HandleFeeType.TAKER)
            break_even_point_price = calc_force_close_offset_price(Decimal(0),
                                                                   total_handle_amt, total_handle_fee,
                                                                   total_handle_units)

            trade_detail.txn_detail_list.append(
                TxnDetail(current_date, total_handle_units, total_handle_amt, total_handle_fee,
                          guarantee,
                          trade_record.price, profit, profit_ratio, last_total_profit + profit,
                          force_close_offset_price,
                          break_even_point_price,
                          max_loss,
                          acct_balance,
                          trade_record))
        elif trade_record.type == TradeType.SELL:
            total_handle_units = last_handle_units - trade_record.unit
            trade_amt = calc_trade_amt(trade_record.price, trade_record.unit)

            if last_handle_units <= 0:
                total_handle_amt = last_handle_amt + trade_amt
                total_handle_fee = last_handle_fee + calc_handle_fee(trade_record.price, trade_record.unit,
                                                                     trade_record.handle_fee_type)
                profit = Decimal(0)
                profit_ratio = Decimal(0)
            else:
                # 買轉賣
                if trade_record.unit > abs(last_handle_units):
                    # 買入單位>之前持有的空倉單位
                    remain_unit = (trade_record.unit * -1 + last_handle_units)
                    total_handle_amt = abs(calc_trade_amt(trade_record.price, remain_unit))
                    total_handle_fee = abs(
                        calc_handle_fee(trade_record.price, remain_unit, trade_record.handle_fee_type))
                    profit = calc_profit(trade_record.price, last_handle_amt, last_handle_fee, last_handle_units,
                                         trade_record.handle_fee_type)
                    profit_ratio = profit / last_trade_detail_guarantee
                else:
                    # 買入單位<之前持有的空倉單位
                    total_handle_amt = last_handle_amt / last_handle_units * total_handle_units
                    total_handle_fee = last_handle_fee / last_handle_units * total_handle_units
                    profit = calc_profit(trade_record.price, last_handle_amt / last_handle_units * trade_record.unit,
                                         calc_handle_fee(last_handle_amt / last_handle_units, trade_record.unit,
                                                         trade_record.handle_fee_type), trade_record.unit,
                                         trade_record.handle_fee_type)
                    profit_ratio = profit / ((last_handle_amt - total_handle_amt) / leverage_ratio).quantize(
                        DECIMAL_PLACE_2, rounding=ROUND_CEILING)

            guarantee = (total_handle_amt / leverage_ratio).quantize(DECIMAL_PLACE_2, rounding=ROUND_CEILING)
            acct_balance = invest_amt + guarantee_amt - guarantee - total_handle_fee
            max_loss = calc_max_loss(binanceKline.high, binanceKline.low, total_handle_amt, total_handle_fee,
                                     total_handle_units,
                                     HandleFeeType.TAKER)
            force_close_offset_price = calc_force_close_offset_price(-1 * (invest_amt + guarantee_amt),
                                                                     total_handle_amt,
                                                                     total_handle_fee,
                                                                     total_handle_units,
                                                                     HandleFeeType.TAKER)
            break_even_point_price = calc_force_close_offset_price(Decimal(0),
                                                                   total_handle_amt, total_handle_fee,
                                                                   total_handle_units)
            trade_detail.txn_detail_list.append(
                TxnDetail(current_date, total_handle_units, total_handle_amt, total_handle_fee,
                          guarantee,
                          trade_record.price, profit, profit_ratio, last_total_profit + profit,
                          force_close_offset_price,
                          break_even_point_price,
                          max_loss,
                          acct_balance,
                          trade_record))
    else:
        profit = calc_profit(current_price, last_handle_amt, last_handle_fee, last_handle_units,
                             HandleFeeType.TAKER)

        profit_ratio = None
        if profit and last_trade_detail_guarantee:
            profit_ratio = profit / last_trade_detail_guarantee

        trade_detail.txn_detail_list.append(
            TxnDetail(current_date, last_handle_units, last_handle_amt, last_handle_fee,
                      last_trade_detail_guarantee,
                      current_price, profit, profit_ratio, last_total_profit + profit,
                      last_trade_detail_force_close_offset_price,
                      last_trade_break_even_point_price, last_trade_max_loss, last_trade_detail_acct_balance,
                      trade_record))


def check_is_force_close_offset(kline: BinanceKline, invest_amt: Decimal, guarantee_amt: Decimal,
                                leverage_ratio: Decimal, trade_detail: TradeDetail):
    # 確認是否爆倉
    latest_txn_detail = trade_detail.txn_detail_list[len(trade_detail.txn_detail_list) - 1]
    # 是否做多
    is_long_trade = latest_txn_detail.units > 0
    # if (latest_txn_detail.force_close_offset_price
    #         and ((is_long_trade and kline.low < latest_txn_detail.force_close_offset_price)
    #              or (not is_long_trade and kline.high > latest_txn_detail.force_close_offset_price))):
    if (is_long_trade and kline.low < latest_txn_detail.force_close_offset_price) or (
            not is_long_trade and kline.high > latest_txn_detail.force_close_offset_price):
        trade_detail.txn_detail_list.append(
            TxnDetail(kline.end_time, Decimal(0), Decimal(0), Decimal(0),
                      Decimal(0),
                      latest_txn_detail.force_close_offset_price, -1 * (invest_amt + guarantee_amt),
                      Decimal(-100 * leverage_ratio), Decimal(0),
                      Decimal(0), -1 * (invest_amt + guarantee_amt), Decimal(0),
                      TradeRecord(kline.end_time, TradeType.SELL if is_long_trade else TradeType.BUY,
                                  latest_txn_detail.force_close_offset_price,
                                  -1 * latest_txn_detail.units,
                                  HandleFeeType.TAKER)))
        return True


if __name__ == '__main__':
    tr1 = TradeRecord(datetime.now(), TradeType.BUY, Decimal(10000), Decimal(100), HandleFeeType.MAKER)
    tr2 = TradeRecord(datetime.now(), TradeType.BUY, Decimal(11000), Decimal(100), HandleFeeType.MAKER)
    tr3 = TradeRecord(datetime.now(), TradeType.SELL, Decimal(12000), Decimal(150), HandleFeeType.MAKER)
    tr4 = TradeRecord(datetime.now(), TradeType.SELL, Decimal(15000), Decimal(100), HandleFeeType.MAKER)
    tr5 = TradeRecord(datetime.now(), TradeType.BUY, Decimal(16000), Decimal(20), HandleFeeType.MAKER)
    tr6 = TradeRecord(datetime.now(), TradeType.BUY, Decimal(18000), Decimal(100), HandleFeeType.MAKER)

    trade_detail = TradeDetail(False, False, [])
    build_txn_detail_list(
        BinanceKline(datetime.now(), Decimal(100), Decimal(100), Decimal(100), Decimal(100), Decimal(100),
                     datetime.now(), 100), Decimal(1000), Decimal(4000), Decimal(100), tr1, trade_detail)
    build_txn_detail_list(
        BinanceKline(datetime.now(), Decimal(100), Decimal(100), Decimal(100), Decimal(100), Decimal(100),
                     datetime.now(), 100), Decimal(1000), Decimal(4000), Decimal(100), tr2, trade_detail)

    build_txn_detail_list(
        BinanceKline(datetime.now(), Decimal(100), Decimal(100), Decimal(100), Decimal(100), Decimal(100),
                     datetime.now(), 100), Decimal(1000), Decimal(4000), Decimal(100), None, trade_detail)

    build_txn_detail_list(
        BinanceKline(datetime.now(), Decimal(100), Decimal(100), Decimal(100), Decimal(100), Decimal(100),
                     datetime.now(), 100), Decimal(1000), Decimal(4000), Decimal(100), tr3, trade_detail)
    build_txn_detail_list(
        BinanceKline(datetime.now(), Decimal(100), Decimal(100), Decimal(100), Decimal(100), Decimal(100),
                     datetime.now(), 100), Decimal(1000), Decimal(4000), Decimal(100), tr4, trade_detail)

    build_txn_detail_list(
        BinanceKline(datetime.now(), Decimal(100), Decimal(100), Decimal(100), Decimal(100), Decimal(100),
                     datetime.now(), 100), Decimal(1000), Decimal(4000), Decimal(100), None, trade_detail)

    build_txn_detail_list(
        BinanceKline(datetime.now(), Decimal(100), Decimal(100), Decimal(100), Decimal(100), Decimal(100),
                     datetime.now(), 100), Decimal(1000), Decimal(4000), Decimal(100), tr5, trade_detail)

    build_txn_detail_list(
        BinanceKline(datetime.now(), Decimal(100), Decimal(100), Decimal(100), Decimal(100), Decimal(100),
                     datetime.now(), 100), Decimal(1000), Decimal(4000), Decimal(100), tr6, trade_detail)

    print(trade_detail.txn_detail_list)
