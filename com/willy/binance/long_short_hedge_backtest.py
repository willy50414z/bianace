from decimal import Decimal

import numpy as np
from binance import Client
from dateutil.relativedelta import relativedelta

from com.willy.binance.dto.hedge_grid_backtest_req import HedgeGridBacktestReq
from com.willy.binance.enums.binance_product import BinanceProduct
from com.willy.binance.service.binance_svc import BinanceSvc
from com.willy.binance.strategy.hedge_strategy import HedgeStrategy
from com.willy.binance.util import type_util
    # TODO 中間價直接上漲突破區間會造成損失
    # TODO 解法: 在區間上沿加一個區間，如果突破區間，可以對沖掉損失，缺點是虧損區間會加大，尤其是區間1上沿跟區間2下沿之間
    # TODO => 用每次交易後庫存計算各價位損益，找出損益區間及最大損失風險
    # TODO => 雙重區間觸發後，找出獲利區間
    # TODO  check > 如果跌回區間1，在觸發區間3前能恢復獲利?
if __name__ == '__main__':
    start_datetime = type_util.str_to_datetime("2025-10-01T00:00:00Z")

    hedge_grid_backtest_res_list_list = []
    for i in range(15):
        # 撈出前一筆收盤價
        binance_svc = BinanceSvc()
        binance_svc.enable_trade_detail_log = False
        binance_svc.enable_hedge_trade_plan_log = False
        binance_svc.enable_trade_summary_log = False

        # 取出開盤價作為區間中點
        klines = binance_svc.get_historical_klines(BinanceProduct.BTCUSDT, Client.KLINE_INTERVAL_5MINUTE,
                                                   start_datetime - relativedelta(**{"minutes": 5}), start_datetime)

        last_close = None
        for kline in klines:
            if kline.start_time == start_datetime:
                last_close = kline.open
        if not last_close:
            raise ValueError("can't get last_close")

        # 計算網格區間: 取出過去2周價格波動，計算網格區間應在包含一個標準差內
        kline_list = binance_svc.get_historical_klines(BinanceProduct.BTCUSDT, Client.KLINE_INTERVAL_1DAY,
                                                       start_datetime - relativedelta(**{"weeks": 2}), start_datetime)
        volatility_list = []
        for kline in kline_list:
            volatility_list.append(kline.high - kline.low)
        std = int(np.std(volatility_list, ddof=1))

        invest_amt = Decimal(1000)
        guarantee_amt = Decimal(3000)
        leverage_ratio_str = Decimal(100)
        level_amt_change = "150%"
        hedge_strategy = HedgeStrategy()
        hedge_grid_backtest_res_list_list.append(
            hedge_strategy.backtest_hedge_grid_list(
                [HedgeGridBacktestReq("std_calc_grid_strategy", BinanceProduct.BTCUSDT,
                                      Client.KLINE_INTERVAL_8HOUR,
                                      int(last_close) - 5000,
                                      int(last_close) + 5000, "10", start_datetime,
                                      start_datetime + relativedelta(**{"days": 2}),
                                      invest_amt, guarantee_amt, level_amt_change,
                                      leverage_ratio_str)
                    , HedgeGridBacktestReq("high_grid_strategy", BinanceProduct.BTCUSDT,
                                           Client.KLINE_INTERVAL_8HOUR,
                                           int(last_close) + 4800,
                                           int(last_close) + 9800, "10", start_datetime,
                                           start_datetime + relativedelta(**{"days": 2}),
                                           invest_amt, guarantee_amt, level_amt_change,
                                           leverage_ratio_str)
                    , HedgeGridBacktestReq("low_grid_strategy", BinanceProduct.BTCUSDT,
                                           Client.KLINE_INTERVAL_8HOUR,
                                           int(last_close) - 9800,
                                           int(last_close) - 4800, "10", start_datetime,
                                           start_datetime + relativedelta(**{"days": 2}),
                                           invest_amt, guarantee_amt, level_amt_change,
                                           leverage_ratio_str)]))

        start_datetime = start_datetime + relativedelta(**{"days": 1})

    prifit_map_list = []
    for hedge_grid_backtest_res_list in hedge_grid_backtest_res_list_list:
        prifit_map = {"trade_detail_long": hedge_grid_backtest_res_list[0].trade_detail_long,
                      "trade_detail_short": hedge_grid_backtest_res_list[0].trade_detail_short, "day": {}}
        for hedge_grid_backtest_res in hedge_grid_backtest_res_list:
            for trade_detail in hedge_grid_backtest_res.trade_detail_long.txn_detail_list:
                if trade_detail.date not in prifit_map["day"]:
                    prifit_map["day"][trade_detail.date] = {}
                if hedge_grid_backtest_res.name not in prifit_map["day"][trade_detail.date]:
                    prifit_map["day"][trade_detail.date][hedge_grid_backtest_res.name] = {}
                prifit_map["day"][trade_detail.date][hedge_grid_backtest_res.name][
                    "buy_profit"] = trade_detail.profit if trade_detail.profit else Decimal(0)

            for trade_detail in hedge_grid_backtest_res.trade_detail_short.txn_detail_list:
                if trade_detail.date not in prifit_map["day"]:
                    prifit_map["day"][trade_detail.date] = {}
                if hedge_grid_backtest_res.name not in prifit_map["day"][trade_detail.date]:
                    prifit_map["day"][trade_detail.date][hedge_grid_backtest_res.name] = {}
                prifit_map["day"][trade_detail.date][hedge_grid_backtest_res.name][
                    "sell_profit"] = trade_detail.profit if trade_detail.profit else Decimal(0)

            for date in prifit_map["day"]:
                buy_profit = prifit_map["day"][date][hedge_grid_backtest_res.name][
                    "buy_profit"] if hedge_grid_backtest_res.name in prifit_map["day"][date] and "buy_profit" in \
                                     prifit_map["day"][date][hedge_grid_backtest_res.name] else Decimal(0)
                sell_profit = prifit_map["day"][date][hedge_grid_backtest_res.name][
                    "sell_profit"] if hedge_grid_backtest_res.name in prifit_map["day"][date] and "sell_profit" in \
                                      prifit_map["day"][date][hedge_grid_backtest_res.name] else Decimal(0)
                if hedge_grid_backtest_res.name not in prifit_map["day"][date]:
                    prifit_map["day"][date][hedge_grid_backtest_res.name] = {}
                prifit_map["day"][date][hedge_grid_backtest_res.name]["profit"] = buy_profit + sell_profit
        prifit_map_list.append(prifit_map)

    total_profit = Decimal(0)
    profit = Decimal(0)
    for prifit_map in prifit_map_list:
        daily_profit_list = []
        for date in prifit_map["day"]:
            daily_profit = Decimal(0)
            for name in prifit_map["day"][date]:
                daily_profit += prifit_map["day"][date][name]["profit"]
            daily_profit_list.append(daily_profit)
            profit = daily_profit
        total_profit += profit
        print(
            f"Date[{next(iter(prifit_map['day']))} ~ {next(reversed(prifit_map['day']))}]break[{prifit_map['trade_detail_long'].is_grid_break}]min_profit[{min(daily_profit_list)}]max_profit[{max(daily_profit_list)}]prifit[{profit}]total_profit[{total_profit}]")

    # profit_list = []
    # for date in prifit_map:
    #     profit = Decimal(0)
    #     for name in prifit_map[date]:
    #         profit += prifit_map[date][name]["profit"]
    #     prifit_map[date]["profit"] = profit
    #     profit_list.append(profit)
    #
    # print(
    #     f"Date[{next(iter(prifit_map))} ~ {next(reversed(prifit_map))}]max_loss[{min(profit_list)}]max_profit[{max(profit_list)}]final_profit[{prifit_map[next(reversed(prifit_map))]['profit']}]")
