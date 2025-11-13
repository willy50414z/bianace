from dataclasses import dataclass
from decimal import Decimal

import pandas as pd
from binance import Client

from com.willy.binance.dto.ma_dca_backtest_req import MaDcaBacktestReq
from com.willy.binance.enums.binance_product import BinanceProduct
from com.willy.binance.enums.trade_type import TradeType
from com.willy.binance.service import trade_svc
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

    return ma7_and_ma25_rel


def get_first_available_trade_amt(trade_level_list: [TradeLevel]):
    for trade_level in trade_level_list:
        if not trade_level.is_trade:
            trade_level.is_trade = True
            return trade_level.amt


def backtest_ma_dca(ma_dca_backtest_req: MaDcaBacktestReq):
    # 用投資金額算出投資層數及金額
    first_layer_invest_amt = calc_first_layer_invest_amt(
        ma_dca_backtest_req.invest_amt * ma_dca_backtest_req.leverage_ratio,
        ma_dca_backtest_req.level_amt_change,
        ma_dca_backtest_req.dca_levels)
    trade_level_list = [TradeLevel]
    for i in range(int(ma_dca_backtest_req.dca_levels)):
        trade_level_list.append(
            TradeLevel(False, first_layer_invest_amt * pow(ma_dca_backtest_req.level_amt_change, i)))

    print(trade_level_list)
    # 撈出股價/MA7/ma25
    binance_svc = BinanceSvc()
    df = binance_svc.get_historical_klines_df(BinanceProduct.BTCUSDT, Client.KLINE_INTERVAL_15MINUTE,
                                              ma_dca_backtest_req.start_time, ma_dca_backtest_req.end_time)
    binance_svc.append_ma(df, 7)
    binance_svc.append_ma(df, 25)
    df = df.dropna(axis=0, how="any")

    # 逐筆確認買進或賣出
    ma7_and_ma25_rel = 0
    for row in df.itertuples(index=False):
        if abs(ma7_and_ma25_rel) > 20:
            trade_record = None
            if ma7_and_ma25_rel > 0:
                # ma7在ma25上面持續超過20期
                if row.ma7 < row.ma25:
                    # ma7如果跌破ma25的時候賣
                    trade_record = trade_svc.create_trade_record(row.start_time, TradeType.SELL, Decimal(row.close),
                                                                 Decimal(
                                                                     get_first_available_trade_amt(trade_level_list)))
            elif ma7_and_ma25_rel < 0:
                if row.ma7 > row.ma25:
                    trade_record = trade_svc.create_trade_record(row.start_time, TradeType.BUY, Decimal(row.close),
                                                                 Decimal(
                                                                     get_first_available_trade_amt(trade_level_list)))
            if trade_record:
                print(f"time[{row.start_time}]trade_record[{trade_record}]")
        ma7_and_ma25_rel = calc_ma7_and_ma25_rel(ma7_and_ma25_rel, row.ma7, row.ma25)


if __name__ == '__main__':
    # binance_svc = BinanceSvc()
    # klines_df = binance_svc.get_historical_klines_df(BinanceProduct.BTCUSDT, Client.KLINE_INTERVAL_15MINUTE,
    #                                      type_util.str_to_datetime("2025-10-01T00:00:00Z"), type_util.str_to_datetime("2025-11-05T00:00:00Z"))
    # print("====BEFORE====")
    # print(klines_df)
    # klines_df.to_csv('data.csv', index=False)

    df_loaded = pd.read_csv('data.csv')
    print("====AFTER====")
    print(df_loaded)
    # invest_amt = Decimal(1000)
    # guarantee_amt = Decimal(4000)
    #
    # req = MaDcaBacktestReq("simple", BinanceProduct.BTCUSDT, type_util.str_to_datetime("2025-10-01T00:00:00Z"),
    #                        type_util.str_to_datetime("2025-11-05T00:00:00Z"), invest_amt, guarantee_amt,
    #                        dca_levels=Decimal(10),
    #                        level_amt_change=Decimal(1.5), leverage_ratio=Decimal(100))
    # backtest_ma_dca(req)
