from dataclasses import dataclass
from decimal import Decimal

import pandas as pd
from dateutil.relativedelta import relativedelta

from com.willy.binance.dto.ma_dca_backtest_req import MaDcaBacktestReq
from com.willy.binance.dto.trade_detail import TradeDetail
from com.willy.binance.enums.binance_product import BinanceProduct
from com.willy.binance.enums.handle_fee_type import HandleFeeType
from com.willy.binance.enums.trade_type import TradeType
from com.willy.binance.service import trade_svc, chart_service
from com.willy.binance.service.binance_svc import BinanceSvc
from com.willy.binance.util import type_util


@dataclass
class TradeLevel:
    is_trade: bool
    amt: Decimal


def calc_first_layer_invest_amt(total_invest_amt: Decimal, level_gap: Decimal, levels: Decimal):
    if levels <= 0:
        return 0.0
    if level_gap == 1:
        return total_invest_amt / levels
    return round(total_invest_amt * (1 - level_gap) / (1 - level_gap ** levels))


def calc_ma7_and_ma25_rel(ma7_and_ma25_rel, ma7, ma25):
    if ma7_and_ma25_rel > 0:
        if ma7 > ma25:
            ma7_and_ma25_rel += 1
        elif ma7 < ma25:
            ma7_and_ma25_rel = -1
    elif ma7_and_ma25_rel < 0:
        if ma7 > ma25:
            ma7_and_ma25_rel = 1
        elif ma7 < ma25:
            ma7_and_ma25_rel += -1
    else:
        if ma7 > ma25:
            ma7_and_ma25_rel = 1
        elif ma7 < ma25:
            ma7_and_ma25_rel = -1
    return ma7_and_ma25_rel


def get_first_available_trade_amt(trade_level_list: [TradeLevel]):
    for trade_level in trade_level_list:
        if not trade_level.is_trade:
            trade_level.is_trade = True
            return trade_level.amt


def reset_trade_level_list_and_get_first(trade_level_list: [TradeLevel]):
    for trade_level in trade_level_list:
        trade_level.is_trade = False
    first_trade_level = trade_level_list[0]
    first_trade_level.is_trade = True
    return first_trade_level.amt


def set_trade_level_by_amt(amt: Decimal, trade_level_list: [TradeLevel]):
    for trade_level in trade_level_list:
        trade_level.is_trade = trade_level.amt < amt


def backtest_ma_dca(ma_dca_backtest_req: MaDcaBacktestReq):
    # 用投資金額算出投資層數及金額
    first_layer_invest_amt = calc_first_layer_invest_amt(
        ma_dca_backtest_req.invest_amt * ma_dca_backtest_req.leverage_ratio,
        ma_dca_backtest_req.level_amt_change,
        ma_dca_backtest_req.dca_levels)
    trade_level_list = []
    for i in range(int(ma_dca_backtest_req.dca_levels)):
        trade_level_list.append(
            TradeLevel(False, first_layer_invest_amt * pow(ma_dca_backtest_req.level_amt_change, i)))

    print(trade_level_list)
    # 撈出股價/MA7/ma25
    binance_svc = BinanceSvc()
    # df = binance_svc.get_historical_klines_df(BinanceProduct.BTCUSDT, Client.KLINE_INTERVAL_15MINUTE,
    #                                           ma_dca_backtest_req.start_time, ma_dca_backtest_req.end_time)

    df = pd.read_csv('E:/code/binance/data/BTCUSDT_15MIN.csv', parse_dates=["start_time", "end_time"])
    # df = df.apply(parse_datetime_row, axis=1)
    mask = (df["start_time"] >= ma_dca_backtest_req.start_time) & (df["start_time"] <= ma_dca_backtest_req.end_time)
    df = df.loc[mask]

    binance_svc.append_ma(df, 7)
    binance_svc.append_ma(df, 6)
    binance_svc.append_ma(df, 25)
    binance_svc.append_ma(df, 99)
    df = df.dropna(axis=0, how="any")

    # 逐筆確認買進或賣出
    ma7_and_ma25_rel = 0
    trade_detail = TradeDetail(False, False, [])
    idx = 0
    date_idx_map = {}
    trade_amt = None
    acct_handle_unit = None
    trade_type = None
    for row in df.itertuples(index=True, name='Row'):
        date_idx_map[row.start_time] = idx
        idx += 1
        if abs(ma7_and_ma25_rel) >= 20:
            now_trade_record = None
            if ma7_and_ma25_rel > 0:
                # ma7在ma25上面持續超過20期
                if row.ma7 < row.ma25:
                    # ma7如果跌破ma25的時候賣
                    last_td = trade_detail.txn_detail_list[len(trade_detail.txn_detail_list) - 1] if len(
                        trade_detail.txn_detail_list) > 0 else None
                    # 如果之前做空，現在也做空，價差至少要>1000
                    if last_td and last_td.trade_record.type == TradeType.SELL and abs(
                            last_td.trade_record.price - Decimal(row.ma7)) < 1000:
                        continue

                    # 如果之前是做多，現在要改做空，所以sell amt要包含之前做多的一起平掉
                    if len(trade_detail.txn_detail_list) > 0:
                        handle_unit = last_td.units
                    else:
                        handle_unit = Decimal(0)

                    if handle_unit > 0:
                        # 之前是做多，改放空的時候要reset trade_amt_list後取得第一階trade amt
                        first_available_trade_amt = reset_trade_level_list_and_get_first(trade_level_list)
                    else:
                        first_available_trade_amt = Decimal(get_first_available_trade_amt(trade_level_list))

                    trade_amt = first_available_trade_amt
                    acct_handle_unit = handle_unit if handle_unit > 0 else Decimal(0)
                    trade_type = TradeType.SELL

                    unit = trade_svc.calc_buyable_units(trade_amt, Decimal(row.open)) + acct_handle_unit
                    now_trade_record = trade_svc.create_trade_record(row.start_time, trade_type, Decimal(row.open),
                                                                     unit=unit, handle_fee_type=HandleFeeType.TAKER)

            elif ma7_and_ma25_rel < 0:
                if row.ma7 > row.ma25:
                    # ma7如果突破ma25的時候買
                    last_td = trade_detail.txn_detail_list[len(trade_detail.txn_detail_list) - 1] if len(
                        trade_detail.txn_detail_list) > 0 else None
                    # 如果之前做多，現在也做多，價差至少要>1000
                    if last_td and last_td.trade_record.type == TradeType.BUY and abs(
                            last_td.trade_record.price - Decimal(row.ma7)) < 1000:
                        continue

                    # 如果之前是做空，現在要改做多，所以buy amt要包含之前做多的一起平掉
                    if len(trade_detail.txn_detail_list) > 0:
                        handle_unit = trade_detail.txn_detail_list[len(trade_detail.txn_detail_list) - 1].units
                    else:
                        handle_unit = Decimal(0)

                    if handle_unit < 0:
                        # 之前是做多，改放空的時候要reset trade_amt_list後取得第一階trade amt
                        first_available_trade_amt = reset_trade_level_list_and_get_first(trade_level_list)
                    else:
                        first_available_trade_amt = Decimal(get_first_available_trade_amt(trade_level_list))

                    trade_amt = first_available_trade_amt
                    acct_handle_unit = handle_unit if handle_unit < 0 else Decimal(0)
                    trade_type = TradeType.BUY

                    unit = trade_svc.calc_buyable_units(trade_amt, Decimal(row.open)) - acct_handle_unit
                    now_trade_record = trade_svc.create_trade_record(row.start_time, trade_type, Decimal(row.open),
                                                                     unit=unit, handle_fee_type=HandleFeeType.TAKER)

            # # 達成條件直接用開盤價進場
            # if now_trade_record:
            #     trade_svc.build_txn_detail_list_df(row,
            #                                        invest_amt,
            #                                        guarantee_amt,
            #                                        ma_dca_backtest_req.leverage_ratio,
            #                                        now_trade_record,
            #                                        trade_detail)

        # 達成條件等MA7才進場
        if trade_amt and trade_amt > 0:
            touch_ma_trade_record = None
            if trade_type == TradeType.BUY:
                # 做多
                if row.open <= row.ma7:
                    # 開盤價已經<=MA7 => 直接買進
                    unit = trade_svc.calc_buyable_units(trade_amt, Decimal(row.open)) - acct_handle_unit
                    touch_ma_trade_record = trade_svc.create_trade_record(row.start_time, TradeType.BUY,
                                                                          Decimal(row.open),
                                                                          unit=unit,
                                                                          handle_fee_type=HandleFeeType.TAKER)
                else:
                    # 開盤價 > MA7 => 等價格跌到MA7再買進
                    last_6_close_avg = df.loc[row.Index - 1].ma6
                    if row.low < last_6_close_avg < row.high:
                        unit = trade_svc.calc_buyable_units(trade_amt, Decimal(last_6_close_avg)) - acct_handle_unit
                        touch_ma_trade_record = trade_svc.create_trade_record(row.start_time, TradeType.BUY,
                                                                              Decimal(last_6_close_avg),
                                                                              unit=unit,
                                                                              handle_fee_type=HandleFeeType.MAKER)
            else:
                # 做空
                if row.open >= row.ma7:
                    # 開盤價已經>=MA7 => 直接賣出
                    unit = trade_svc.calc_buyable_units(trade_amt, Decimal(row.open)) + acct_handle_unit
                    touch_ma_trade_record = trade_svc.create_trade_record(row.start_time, TradeType.SELL,
                                                                          Decimal(row.open),
                                                                          unit=unit,
                                                                          handle_fee_type=HandleFeeType.TAKER)
                else:
                    # 開盤價 < MA7 => 等價格漲到MA7再賣出
                    last_6_close_avg = df.loc[row.Index - 1].ma6
                    if row.low < last_6_close_avg < row.high:
                        unit = trade_svc.calc_buyable_units(trade_amt, Decimal(last_6_close_avg)) + acct_handle_unit
                        touch_ma_trade_record = trade_svc.create_trade_record(row.start_time, TradeType.SELL,
                                                                              Decimal(last_6_close_avg),
                                                                              unit=unit,
                                                                              handle_fee_type=HandleFeeType.MAKER)
            if touch_ma_trade_record:
                trade_svc.build_txn_detail_list_df(row,
                                                   invest_amt,
                                                   guarantee_amt,
                                                   ma_dca_backtest_req.leverage_ratio,
                                                   touch_ma_trade_record,
                                                   trade_detail)
                trade_amt = None
                trade_unit = None

        ma7_and_ma25_rel = calc_ma7_and_ma25_rel(ma7_and_ma25_rel, row.ma7, row.ma25)

        # 如果是假突破或假跌破(5K內又跌/漲回去)，把買/賣的賣/買回來
        if len(trade_detail.txn_detail_list) > 1:
            last_1_td = trade_detail.txn_detail_list[len(trade_detail.txn_detail_list) - 1]
            last_2_td = trade_detail.txn_detail_list[len(trade_detail.txn_detail_list) - 2]
            # 近2個交易是做反向交易
            if last_1_td.trade_record.type != last_2_td.trade_record.type \
                    and ((last_1_td.trade_record.type == TradeType.BUY and row.ma7 < row.ma25 and (
                    date_idx_map[row.start_time] - date_idx_map[last_1_td.trade_record.date]) < 10) \
                         or (last_1_td.trade_record.type == TradeType.SELL and row.ma7 > row.ma25 and (
                            date_idx_map[row.start_time] - date_idx_map[last_1_td.trade_record.date]) < 10)):
                # set trade amt
                set_trade_level_by_amt(last_2_td.handle_amt, trade_level_list)
                # build trade record
                trade_type = TradeType.BUY if last_1_td.trade_record.type == TradeType.SELL else TradeType.SELL
                touch_ma_trade_record = trade_svc.create_trade_record(row.start_time, trade_type, Decimal(row.close),
                                                                      unit=last_1_td.trade_record.unit,
                                                                      handle_fee_type=HandleFeeType.TAKER)
                trade_svc.build_txn_detail_list_df(row,
                                                   invest_amt,
                                                   guarantee_amt,
                                                   ma_dca_backtest_req.leverage_ratio,
                                                   touch_ma_trade_record,
                                                   trade_detail)

    for txn_detail in trade_detail.txn_detail_list:
        df.loc[df['start_time'] == txn_detail.date, 'txn_detail'] = txn_detail

    chart_service.export_trade_point_chart("ma_dca_ma", df)

    print("date\tis_ma25_up\tunit\thandle_amt\thandle_fee\tprice\tprofit\ttotal_profit\ttr.type\ttr.unit")
    for td in trade_detail.txn_detail_list:
        is_ma25_up = None
        # for idx, row in df.itertuples():
        #     if df.itertuples()[idx].end_date == td.date:
        #         is_ma25_up = df.itertuples()[idx].ma25 > df.itertuples()[idx - 1].ma25
        print(
            f"{td.date + relativedelta(**{'hours': 0})}\t{is_ma25_up}\t{td.units}\t{td.handle_amt}\t{td.handling_fee}\t{td.current_price}\t{td.profit}\t{td.total_profit}\t{td.trade_record.type}\t{td.trade_record.unit}")


if __name__ == '__main__':
    invest_amt = Decimal(5000)
    guarantee_amt = Decimal(5000)

    req = MaDcaBacktestReq("simple", BinanceProduct.BTCUSDT, type_util.str_to_datetime("2025-08-01T00:00:00Z"),
                           type_util.str_to_datetime("2025-11-05T00:00:00Z"), invest_amt, guarantee_amt,
                           dca_levels=Decimal(10),
                           level_amt_change=Decimal(1.5), leverage_ratio=Decimal(100))
    backtest_ma_dca(req)
