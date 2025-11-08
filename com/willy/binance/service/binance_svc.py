import datetime
import logging
import math
from datetime import timezone
from decimal import Decimal, ROUND_FLOOR
from typing import List

from binance import Client

from com.willy.binance.config.config_util import config_util
from com.willy.binance.config.const import DECIMAL_PLACE_2
from com.willy.binance.dto.binance_kline import BinanceKline
from com.willy.binance.dto.fixed_price_invest_amt_dto import FixedPriceInvestAmtDto
from com.willy.binance.dto.hedge_trade_price_amt import HedgeTradePriceAmt
from com.willy.binance.dto.trade_plan import TradePlan
from com.willy.binance.enum import trade_type
from com.willy.binance.enum.binance_product import BinanceProduct
from com.willy.binance.enum.handle_fee_type import HandleFeeType
from com.willy.binance.enum.trade_type import TradeType
from com.willy.binance.service import trade_svc
from com.willy.binance.util import type_util


def calc_first_layer_invest_amt(total_invest_amt: Decimal, level_gap: Decimal, levels: Decimal):
    single_side_invest_amt = total_invest_amt / 2
    if levels <= 0:
        return 0.0
    if level_gap == 1:
        return single_side_invest_amt / levels
    return round(single_side_invest_amt * (1 - level_gap) / (1 - level_gap ** levels))


class BinanceSvc:
    config = config_util("binance.acct.hedgebuy")
    client = Client(config.get("apikey"), config.get("privatekey"))

    def get_historical_klines(self, binance_product: BinanceProduct, kline_interval=Client.KLINE_INTERVAL_1DAY,
                              start_date: datetime = type_util.str_to_datetime("20250101"),
                              end_date: datetime = type_util.str_to_datetime("20250105")):
        klines = self.client.get_historical_klines(binance_product.name, kline_interval,
                                                   int(start_date.timestamp() * 1000),
                                                   int(end_date.timestamp() * 1000))
        kline_list = []
        for kline in klines:
            kline_list.append(
                BinanceKline(start_time=type_util.timestamp_to_datetime(kline[0] // 1000, tz=timezone.utc),
                             open=Decimal(kline[1]),
                             high=Decimal(kline[2]), low=Decimal(kline[3]), close=Decimal(kline[4]),
                             vol=Decimal(kline[5]),
                             end_time=type_util.timestamp_to_datetime(kline[6] // 1000, tz=timezone.utc),
                             number_of_trade=kline[8]))
        return kline_list

    def backtest_hedge_grid(self, binance_product: BinanceProduct, lower_bound: int, upper_bound: int, grid_levels: str,
                            start_time: datetime.datetime, end_time: datetime.datetime, invest_amt: Decimal,
                            level_amt_change: str, leverage_ratio: Decimal):
        """
        回測買賣對沖策略損益

        :param binance_product:
        :param lower_bound:
        :param upper_bound:
        :param grid_levels:
        網格劃分數量
        可以是'10'表示劃分成10格做交易
        也可以是'5%'表示每5%為一格
        :param start_time:
        :param end_time:
        :param invest_amt:
        :param level_amt_change:
        每網格，投資金額調整多少
        可以是'500'表示每一網格投資金額差距為500
        也可以是'5%'表示每一網格投資金額差距為5%
        :param leverage_ratio:
        :return:
        """

        # print出回測資訊
        logging.info(
            f"product[{binance_product}]start_time[{type_util.datetime_to_str(start_time)}]end_time[{type_util.datetime_to_str(end_time)}]")
        logging.info(
            f"price range[{lower_bound} - {upper_bound}]grid_levels[{grid_levels}]invest_amt[{invest_amt}]level_amt_change[{level_amt_change}]leverage_ratio[{leverage_ratio}]")

        # 計算買賣策略
        ## 計算網格價格
        trade_price = upper_bound
        trade_price_list = []
        if grid_levels.endswith("%"):
            grid_gap_ratio = Decimal(grid_levels[0:len(grid_levels) - 1])
            while trade_price >= lower_bound:
                # hedge_trade_price_amt_list.append(HedgeTradePriceAmt(price=trade_price, buy_amt=))
                trade_price = trade_price * (1 - grid_gap_ratio / 100)
            raise ValueError("grid_levels end with % is not implement")
        else:
            grid_gap = (upper_bound - lower_bound) // int(grid_levels)
            while trade_price >= lower_bound:
                trade_price_list.append(trade_price)
                trade_price -= grid_gap

        # 計算第一層投入金額
        invest_amt_list = []
        first_layer_invest_amt = 0
        if level_amt_change.endswith("%"):
            levels_amt_gap = Decimal(level_amt_change[:len(level_amt_change) - 1]) / 100
            first_layer_invest_amt = calc_first_layer_invest_amt(invest_amt * leverage_ratio,
                                                                 levels_amt_gap,
                                                                 Decimal(len(trade_price_list)))
            last_layer_invest_amt = first_layer_invest_amt
            for i in range(len(trade_price_list)):
                invest_amt_list.append(Decimal(last_layer_invest_amt))
                last_layer_invest_amt = math.floor(last_layer_invest_amt * levels_amt_gap)
        else:
            raise ValueError(f"level_amt_change should end with '%' but level_amt_change[{level_amt_change}]")

        ## 印出網格投資表
        hedge_buy_list = []
        hedge_sell_list = []
        for i in range(len(trade_price_list)):
            hedge_buy_list.append(FixedPriceInvestAmtDto(False, Decimal(trade_price_list[i]), invest_amt_list[i]))
            hedge_sell_list.append(
                FixedPriceInvestAmtDto(False, Decimal(trade_price_list[i]),
                                       invest_amt_list[len(trade_price_list) - i - 1]))

        logging.info("      \tbuy amt\tsell amt")
        for hedge_trade_idx in range(len(hedge_buy_list)):
            logging.info(
                f"{hedge_buy_list[hedge_trade_idx].price}\t{hedge_buy_list[hedge_trade_idx].amt}\t{hedge_sell_list[hedge_trade_idx].amt}")

        daily_kline_list = self.get_historical_klines(binance_product, start_date=start_time, end_date=end_time)

        single_side_invest_amt = (invest_amt / 2).quantize(DECIMAL_PLACE_2, ROUND_FLOOR)

        hedge_buy_trade_detail_list = self.get_trade_detail_list(binance_product, start_time, end_time, TradeType.BUY,
                                                                 single_side_invest_amt, leverage_ratio,
                                                                 daily_kline_list, hedge_buy_list)

        hedge_sell_trade_detail_list = self.get_trade_detail_list(binance_product, start_time, end_time, TradeType.SELL,
                                                                  single_side_invest_amt,
                                                                  leverage_ratio,
                                                                  daily_kline_list, hedge_sell_list)

        for trade_detail in hedge_buy_trade_detail_list:
            print(trade_detail)

        print("==============")

        for trade_detail in hedge_sell_trade_detail_list:
            print(trade_detail)

        if len(hedge_buy_trade_detail_list) == len(hedge_sell_trade_detail_list):
            for i in range(len(hedge_buy_trade_detail_list)):
                hedge_buy_trade_detail = hedge_buy_trade_detail_list[i]
                if hedge_buy_trade_detail.profit and hedge_sell_trade_detail_list[i].profit:
                    print(
                        f"date[{hedge_buy_trade_detail.date}]current_price[{hedge_buy_trade_detail.current_price}]"
                        f"buy_profit[{hedge_buy_trade_detail.profit}]"
                        f"sell_profit[{hedge_sell_trade_detail_list[i].profit}]"
                        f"total_profit[{hedge_buy_trade_detail.profit + hedge_sell_trade_detail_list[i].profit}]")

        # buy_acct_trade_record = []
        # sell_acct_trade_record = []
        # buy_trade_detail_list = []
        # sell_trade_detail_list = []
        # for daily_kline in daily_kline_list:
        #     # 逐日確定是否觸發交易
        #     # logging.info(daily_kline)
        #     for hedge_trade_price_amt in hedge_trade_price_amt_list:
        #         if not hedge_trade_price_amt.has_trade and daily_kline.high > hedge_trade_price_amt.price and daily_kline.low < hedge_trade_price_amt.price:
        #             # five_minutes_kline_list = self.get_historical_klines(binance_product, Client.KLINE_INTERVAL_5MINUTE, start_date=daily_kline.start_time, end_date=daily_kline.end_time)
        #             hedge_trade_price_amt.has_trade = True
        #
        #             # 觸發交易時紀錄交易紀錄
        #             trade_record = trade_svc.create_trade_record(daily_kline.start_time, TradeType.BUY,
        #                                                          hedge_trade_price_amt.price,
        #                                                          hedge_trade_price_amt.buy_amt, HandleFeeType.MAKER)
        #
        #             if trade_record:
        #                 buy_acct_trade_record.append(trade_record)
        #                 trade_svc.build_trade_detail_list(daily_kline.close,
        #                                                   Decimal(invest_amt),
        #                                                   leverage_ratio,
        #                                                   [trade_record],
        #                                                   daily_kline_list[len(daily_kline_list) - 1].end_time,
        #                                                   buy_trade_detail_list)
        #                 # print(buy_trade_detail_list[len(buy_trade_detail_list) - 1])
        #
        #             trade_record = trade_svc.create_trade_record(daily_kline.start_time, TradeType.SELL,
        #                                                          hedge_trade_price_amt.price,
        #                                                          hedge_trade_price_amt.sellAmt, HandleFeeType.MAKER)
        #
        #             if trade_record:
        #                 sell_acct_trade_record.append(trade_record)
        #                 trade_svc.build_trade_detail_list(daily_kline.close,
        #                                                   Decimal(invest_amt),
        #                                                   leverage_ratio,
        #                                                   [trade_record],
        #                                                   daily_kline_list[len(daily_kline_list) - 1].end_time,
        #                                                   sell_trade_detail_list)
        #                 # print(sell_trade_detail_list[len(sell_trade_detail_list) - 1])
        #
        # for buy_trade_detail in buy_trade_detail_list:
        #     print(buy_trade_detail)
        #
        # print("==============")
        #
        # for buy_trade_detail in sell_trade_detail_list:
        #     print(buy_trade_detail)

        # if len(buy_acct_trade_record) > 0:
        #     logging.info(
        #         trade_svc.build_trade_detail_list(daily_kline_list[len(daily_kline_list) - 1].close, Decimal(invest_amt),
        #                                           leverage_ratio,
        #                                           buy_acct_trade_record,
        #                                           daily_kline_list[len(daily_kline_list) - 1].end_time))
        #
        # if len(sell_acct_trade_record) > 0:
        #     logging.info(
        #         trade_svc.build_trade_detail_list(daily_kline_list[len(daily_kline_list) - 1].close, Decimal(invest_amt),
        #                                           leverage_ratio,
        #                                           sell_acct_trade_record,
        #                                           daily_kline_list[len(daily_kline_list) - 1].end_time))

    def get_trade_detail_list(self, binance_product: BinanceProduct, start_time: datetime.datetime,
                              end_time: datetime.datetime,
                              trade_type: TradeType,
                              invest_amt: Decimal,
                              leverage_ratio: Decimal,
                              daily_kline_list: List[BinanceKline] = None,
                              trade_plan_list=None):
        if trade_plan_list is None:
            trade_plan_list = []

        if daily_kline_list is None:
            daily_kline_list = self.get_historical_klines(binance_product, start_date=start_time, end_date=end_time)

        trade_detail_list = []
        for daily_kline in daily_kline_list:
            trade_record_list = []
            # 逐日確定是否觸發交易
            for trade_plan in trade_plan_list:
                if isinstance(trade_plan, FixedPriceInvestAmtDto):
                    if not trade_plan.is_traded and daily_kline.high > trade_plan.price > daily_kline.low:
                        # five_minutes_kline_list = self.get_historical_klines(binance_product, Client.KLINE_INTERVAL_5MINUTE, start_date=daily_kline.start_time, end_date=daily_kline.end_time)
                        trade_plan.is_traded = True

                        # 觸發交易時紀錄交易紀錄
                        trade_record = trade_svc.create_trade_record(daily_kline.start_time, trade_type,
                                                                     trade_plan.price,
                                                                     trade_plan.amt, HandleFeeType.MAKER)
                        if trade_record:
                            trade_record_list.append(trade_record)
            if len(trade_record_list) > 0:
                for trade_record in trade_record_list:
                    trade_svc.build_trade_detail_list(daily_kline.end_time, daily_kline.close,
                                                      Decimal(invest_amt),
                                                      leverage_ratio,
                                                      trade_record,
                                                      trade_detail_list)
            else:
                trade_svc.build_trade_detail_list(daily_kline.end_time, daily_kline.close,
                                                  Decimal(invest_amt),
                                                  leverage_ratio,
                                                  None,
                                                  trade_detail_list)
        return trade_detail_list


if __name__ == '__main__':
    # print(calc_current_price(-203619.2, 103471.35, 203619.2))
    # print(calc_profit(101101.9, 103471.35, 203619.2))
    # print(calc_first_layer_invest_amt(1625, 1.5, 4))
    bianace_svc = BinanceSvc()
    # bianace_svc.backtest_hedge_grid(BinanceProduct.BTCUSDT, 88000, 98000, "10",
    #                                  type_util.str_to_datetime("20250101"), type_util.str_to_datetime("20250201"),
    #                                  Decimal(10000), "150%", Decimal(100))

    bianace_svc.backtest_hedge_grid(BinanceProduct.BTCUSDT, 97000, 107000, "10",
                                    type_util.str_to_datetime("20250101"), type_util.str_to_datetime("20250201"),
                                    Decimal(5000), "150%", Decimal(100))

    # TODO 中間價直接上漲突破區間會造成損失
    # TODO 解法: 在區間上沿加一個區間，如果突破區間，可以對沖掉損失，缺點是虧損區間會加大，尤其是區間1上沿跟區間2下沿之間
    # TODO => 用每次交易後庫存計算各價位損益，找出損益區間及最大損失風險
    # TODO => 雙重區間觸發後，找出獲利區間
    # TODO  check > 如果跌回區間1，在觸發區間3前能恢復獲利?
