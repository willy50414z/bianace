from datetime import timedelta
from decimal import Decimal

import pandas as pd

from com.willy.binance.dto.trade_detail import TradeDetail
from com.willy.binance.dto.trade_record import TradeRecord
from com.willy.binance.enums.handle_fee_type import HandleFeeType
from com.willy.binance.enums.trade_reason import TradeReason, TradeReasonType
from com.willy.binance.enums.trade_type import TradeType
from com.willy.binance.service import tech_idx_svc, trade_svc
from com.willy.binance.strategy.ma_dca_strategy import TradeLevel
from com.willy.binance.strategy.trade_strategy import TradingStrategy


def calc_first_layer_invest_amt(total_invest_amt: Decimal, level_gap: Decimal, levels: Decimal):
    if levels <= 0:
        return 0.0
    if level_gap == 1:
        return total_invest_amt / levels
    return round(total_invest_amt * (1 - level_gap) / (1 - level_gap ** levels))


def reset_trade_level_list_and_get_first(trade_level_list: [TradeLevel]):
    for trade_level in trade_level_list:
        trade_level.is_trade = False
    first_trade_level = trade_level_list[0]
    first_trade_level.is_trade = True
    return first_trade_level.amt


def get_first_available_trade_amt(trade_level_list: [TradeLevel]):
    for trade_level in trade_level_list:
        if not trade_level.is_trade:
            trade_level.is_trade = True
            return trade_level.amt
    return Decimal(0)


def reset_available_trade_amt(trade_level_list: [TradeLevel]):
    for trade_level in trade_level_list:
        trade_level.is_trade = False


def set_trade_level_by_amt(amt: Decimal, trade_level_list: [TradeLevel]):
    for trade_level in trade_level_list:
        if not trade_level.is_trade:
            trade_level.is_trade = True
            return


def trade_if_not_trade_twice(row,
                             invest_amt,
                             guarantee_amt,
                             leverage_ratio,
                             now_trade_record,
                             trade_detail, trade_level_list):
    if now_trade_record:
        if len(trade_detail.txn_detail_list) > 0:
            last_td = trade_detail.txn_detail_list[len(trade_detail.txn_detail_list) - 1]
            if last_td.trade_record.type == now_trade_record.type and last_td.units != 0:
                # 上一次是同向交易 => 直接平倉 因為同向交易發生時，大多會虧損
                reset_available_trade_amt(trade_level_list)
                return trade_svc.create_close_trade_record(now_trade_record.date,
                                                           now_trade_record.price, last_td,
                                                           reason=TradeReason(
                                                               TradeReasonType.PASSIVE,
                                                               "同向交易攤平"))

    return now_trade_record


class MovingAverageStrategy(TradingStrategy):
    ma7_and_ma25_rel = 0
    invest_amt = 0
    guarantee_amt = 0
    trade_level_list = []

    def get_trade_record(self, row: pd.Series, trade_detail: TradeDetail) -> TradeRecord:
        last_ma7_and_ma25_rel = self.ma7_and_ma25_rel
        self.update_ma7_and_ma25_rel(row.ma7, row.ma25)
        last_td = self.trade_detail.txn_detail_list[len(self.trade_detail.txn_detail_list) - 1] if len(
            self.trade_detail.txn_detail_list) > 0 else None

        trade_record = self.trade_if_cross_ma(last_td, last_ma7_and_ma25_rel, row)
        if trade_record:
            return trade_record

        # 3. 獲利時，MA7/MA25連續3期逐漸變小且<100點 => 停利
        trade_record = self.get_stop_loss_trade_record(last_td, row, self.leverage, trade_detail, self.trade_level_list)
        if trade_record:
            return trade_record

        # 如果是假突破或假跌破(5K內又跌/漲回去)，把買/賣的賣/買回來
        trade_record = self.fake_break(row)
        if trade_record:
            return trade_record

    @property
    def invest_and_guarantee_ratio(self) -> float:
        return 0.5

    def prepare_data(self, initial_capital: int, df: pd.DataFrame, other_args: dict):
        tech_idx_svc.append_ma(df, 7)
        tech_idx_svc.append_ma(df, 6)
        tech_idx_svc.append_ma(df, 25)
        tech_idx_svc.append_ma(df, 99)

        # MA過去20天是否都上漲/下跌
        df['ma25_diff'] = df['ma25'].diff()

        diff_int = df['ma25_diff'] > 0
        diff_int = diff_int.astype(int)
        past20_growth = diff_int.rolling(window=20, min_periods=20).min()
        df['past20_ma25_growth'] = past20_growth.astype(bool)

        diff_ma25_diff = df['ma25_diff'] < 0
        diff_int = diff_ma25_diff.astype(int)
        past20_ma25_fall = diff_int.rolling(window=20, min_periods=20).min()
        df['past20_ma25_fall'] = past20_ma25_fall.astype(bool)

        # 用投資金額算出投資層數及金額
        first_layer_invest_amt = calc_first_layer_invest_amt(
            Decimal(self.invest_amt * self.leverage),
            self.other_args["level_amt_change"],
            self.other_args["dca_levels"])

        for i in range(int(self.other_args["dca_levels"])):
            self.trade_level_list.append(
                TradeLevel(False, first_layer_invest_amt * pow(self.other_args["level_amt_change"], i)))

    @property
    def lookback_days(self) -> timedelta:
        return timedelta(minutes=15 * 99)

    def update_ma7_and_ma25_rel(self, ma7, ma25):
        if self.ma7_and_ma25_rel > 0:
            if ma7 > ma25:
                self.ma7_and_ma25_rel += 1
            elif ma7 < ma25:
                self.ma7_and_ma25_rel = -1
        elif self.ma7_and_ma25_rel < 0:
            if ma7 > ma25:
                self.ma7_and_ma25_rel = 1
            elif ma7 < ma25:
                self.ma7_and_ma25_rel += -1
        else:
            if ma7 > ma25:
                self.ma7_and_ma25_rel = 1
            elif ma7 < ma25:
                self.ma7_and_ma25_rel = -1

    def trade_if_cross_ma(self, last_td, last_ma7_and_ma25_rel, row):
        # 1. MA7 / MA25 超過20期沒有交叉 > 交叉後確立做多/空方向
        if abs(last_ma7_and_ma25_rel) >= 20:
            if last_ma7_and_ma25_rel > 0:
                # ma7在ma25上面持續超過20期
                if row.ma7 < row.ma25 and not row.past20_ma25_growth:
                    # ma7如果跌破ma25的時候賣
                    # # 如果之前做空，現在也做空，價差至少要>1000
                    # if last_td and last_td.trade_record.type == TradeType.SELL and abs(
                    #         last_td.trade_record.price - Decimal(row.ma7)) < 1000:
                    #     continue

                    # 如果之前是做多，現在要改做空，所以sell amt要包含之前做多的一起平掉
                    if len(self.trade_detail.txn_detail_list) > 0:
                        handle_unit = last_td.units
                    else:
                        handle_unit = Decimal(0)

                    if handle_unit > 0:
                        # 之前是做多，改放空的時候要reset trade_amt_list後取得第一階trade amt
                        first_available_trade_amt = reset_trade_level_list_and_get_first(self.trade_level_list)
                    else:
                        first_available_trade_amt = Decimal(get_first_available_trade_amt(self.trade_level_list))

                    trade_amt = first_available_trade_amt
                    acct_handle_unit = handle_unit if handle_unit > 0 else Decimal(0)
                    trade_type = TradeType.SELL

                    unit = trade_svc.calc_buyable_units(trade_amt, Decimal(row.open)) + acct_handle_unit
                    now_trade_record = trade_svc.create_trade_record(row.start_time, trade_type, Decimal(row.open),
                                                                     unit=unit, handle_fee_type=HandleFeeType.TAKER,
                                                                     reason=TradeReason(TradeReasonType.ACTIVE,
                                                                                        "符合條件"))

                    # 6. 連續2次符合條件且方向相同，直接平倉
                    return trade_if_not_trade_twice(row,
                                                    self.invest_amt,
                                                    self.guarantee_amt,
                                                    self.leverage,
                                                    now_trade_record,
                                                    self.trade_detail, self.trade_level_list)
            elif last_ma7_and_ma25_rel < 0:
                if row.ma7 > row.ma25 and not row.past20_ma25_fall:
                    # ma7如果突破ma25的時候買
                    # # 如果之前做多，現在也做多，價差至少要>1000
                    # if last_td and last_td.trade_record.type == TradeType.BUY and abs(
                    #         last_td.trade_record.price - Decimal(row.ma7)) < 1000:
                    #     continue

                    # 如果之前是做空，現在要改做多，所以buy amt要包含之前做多的一起平掉
                    if len(self.trade_detail.txn_detail_list) > 0:
                        handle_unit = self.trade_detail.txn_detail_list[
                            len(self.trade_detail.txn_detail_list) - 1].units
                    else:
                        handle_unit = Decimal(0)

                    if handle_unit < 0:
                        # 之前是做多，改放空的時候要reset trade_amt_list後取得第一階trade amt
                        first_available_trade_amt = reset_trade_level_list_and_get_first(self.trade_level_list)
                    else:
                        first_available_trade_amt = Decimal(get_first_available_trade_amt(self.trade_level_list))

                    trade_amt = first_available_trade_amt
                    acct_handle_unit = handle_unit if handle_unit < 0 else Decimal(0)
                    trade_type = TradeType.BUY

                    unit = trade_svc.calc_buyable_units(trade_amt, Decimal(row.open)) - acct_handle_unit
                    now_trade_record = trade_svc.create_trade_record(row.start_time, trade_type, Decimal(row.open),
                                                                     unit=unit, handle_fee_type=HandleFeeType.TAKER,
                                                                     reason=TradeReason(TradeReasonType.ACTIVE,
                                                                                        "符合條件"))

                    # 6. 連續2次符合條件且方向相同，直接平倉
                    return trade_if_not_trade_twice(row,
                                                    self.invest_amt,
                                                    self.guarantee_amt,
                                                    self.leverage,
                                                    now_trade_record,
                                                    self.trade_detail, self.trade_level_list)

    def get_stop_loss_trade_record(self, last_td, row, leverage_ratio, trade_detail, trade_level_list):
        if last_td:
            unrealize_profit = trade_svc.calc_profit(row.close, last_td.handle_amt, last_td.handling_fee, last_td.units)
            if unrealize_profit and unrealize_profit > 0:
                is_need_close = False
                # if abs(df.iloc[i - 2].ma7 - df.iloc[i - 2].ma25) > abs(df.iloc[i - 1].ma7 - df.iloc[i - 1].ma25) > abs(
                #         df.iloc[i].ma7 - df.iloc[i].ma25) < 100:
                #     is_need_close = True
                #
                # if is_need_close:
                #     trade_svc.build_txn_detail_list_df(row,
                #                                        invest_amt,
                #                                        guarantee_amt,
                #                                        ma_dca_backtest_req.leverage_ratio,
                #                                        trade_svc.create_close_trade_record(row.start_time, row.close,
                #                                                                            last_td, reason="停利"),
                #                                        trade_detail)
                #     reset_available_trade_amt(trade_level_list)
            elif unrealize_profit and unrealize_profit < 0:
                # 5. 虧損超過1000點 => 停損
                if last_td.units > 0 and (last_td.handle_amt / last_td.units - Decimal(row.low)) > 1000:
                    reset_available_trade_amt(trade_level_list)
                    return trade_svc.create_close_trade_record(row.start_time, round(
                        last_td.handle_amt / last_td.units, 2) - 1000, last_td,
                                                               reason=TradeReason(
                                                                   TradeReasonType.PASSIVE,
                                                                   "停損"))
                if last_td.units < 0 and (Decimal(row.high) + last_td.handle_amt / last_td.units) > 1000:
                    reset_available_trade_amt(trade_level_list)
                    return trade_svc.create_close_trade_record(row.start_time, round(
                        last_td.handle_amt / last_td.units * -1, 2) + 1000, last_td,
                                                               reason=TradeReason(
                                                                   TradeReasonType.PASSIVE,
                                                                   "停損"))

    def fake_break(self, row):
        if len(self.trade_detail.txn_detail_list) > 1:
            non_stop_loss_td_list = [td for td in self.trade_detail.txn_detail_list if
                                     td.trade_record.reason.trade_reason_type != TradeReasonType.PASSIVE]
            last_1_td = non_stop_loss_td_list[len(non_stop_loss_td_list) - 1]
            last_2_td = non_stop_loss_td_list[len(non_stop_loss_td_list) - 2]

            # last_1_td = trade_detail.txn_detail_list[len(trade_detail.txn_detail_list) - 1]
            # last_2_td = trade_detail.txn_detail_list[len(trade_detail.txn_detail_list) - 2]
            # 近2個交易是做反向交易
            # 賣>買>馬上跌破 > 賣
            # 買>賣>馬上突破 > 買
            if last_1_td.trade_record.type != last_2_td.trade_record.type \
                    and ((last_1_td.trade_record.type == TradeType.BUY and row.ma7 < row.ma25 and (
                    self.date_idx_map[row.start_time] - self.date_idx_map[last_1_td.trade_record.date]) < 10) \
                         or (last_1_td.trade_record.type == TradeType.SELL and row.ma7 > row.ma25 and (
                            self.date_idx_map[row.start_time] - self.date_idx_map[last_1_td.trade_record.date]) < 10)):
                # set trade amt
                set_trade_level_by_amt(last_2_td.handle_amt, self.trade_level_list)
                # build trade record
                trade_type = TradeType.BUY if last_1_td.trade_record.type == TradeType.SELL else TradeType.SELL
                touch_ma_trade_record = trade_svc.create_trade_record(row.start_time, trade_type,
                                                                      Decimal(row.close),
                                                                      unit=abs(last_2_td.units) + abs(last_1_td.units),
                                                                      handle_fee_type=HandleFeeType.TAKER,
                                                                      reason=TradeReason(
                                                                          TradeReasonType.ACTIVE,
                                                                          "假突跌破，認錯回補"))
                return touch_ma_trade_record
