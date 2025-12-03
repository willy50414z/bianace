from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from decimal import Decimal

import pandas as pd
from binance import Client

from com.willy.binance.dao import binance_kline_dao
from com.willy.binance.dto.trade_detail import TradeDetail
from com.willy.binance.dto.trade_record import TradeRecord
from com.willy.binance.enums.binance_product import BinanceProduct
from com.willy.binance.enums.trade_reason import TradeReason, TradeReasonType
from com.willy.binance.service import trade_svc, chart_service
from com.willy.binance.service.binance_svc import BinanceSvc


class TradingStrategy(ABC):
    def __init__(self, test_name, start_time: datetime,
                 end_time: datetime,
                 initial_capital: int,
                 product: BinanceProduct,
                 leverage: int, other_args: dict):
        self.test_name = test_name
        self.start_time = start_time
        self.end_time = end_time
        self.initial_capital = initial_capital
        self.product = product
        self.leverage = leverage
        self.other_args = other_args
        self.invest_amt = round(float(self.invest_and_guarantee_ratio * initial_capital), 2)
        self.guarantee_amt = initial_capital - self.invest_amt
        self.binance_svc = BinanceSvc()
        self.trade_detail = TradeDetail(False, False, [])
        self.date_idx_map = {}

    @property
    @abstractmethod
    def lookback_days(self) -> timedelta:
        pass

    @property
    @abstractmethod
    def invest_and_guarantee_ratio(self) -> float:
        pass

    @abstractmethod
    def prepare_data(self, initial_capital: int, df: pd.DataFrame, other_args: dict) -> pd.DataFrame:
        """
        [強制實現] 接收原始歷史數據，計算指標 (如 MA, RSI) 並返回。
        """
        pass

    @abstractmethod
    def get_trade_record_by_date(self, dt: datetime) -> TradeRecord:
        """

        """
        pass

    @abstractmethod
    def get_trade_record(self, row: pd.Series, trade_detail: TradeDetail) -> TradeRecord:
        """
        [強制實現] 根據當前數據和持倉，決定當日的交易量和原因。

        Args:
            trade_detail:
            row: 當前日期的數據 (包含指標)。

        Returns:
            tuple: (units_change, reason)
                   units_change > 0 買入, units_change < 0 賣出, units_change = 0 不操作
        """
        pass

    def run_backtest(self):
        # print(f"===== 啟動回測引擎: {product} =====")

        # 1. 計算數據撈取範圍
        data_fetch_start = self.start_time - self.lookback_days

        # 2. 獲取並準備數據
        df = binance_kline_dao.get_kline(self.product, Client.KLINE_INTERVAL_15MINUTE, data_fetch_start, self.end_time)
        df.set_index('start_time')
        self.prepare_data(self.initial_capital, df, self.other_args)

        # 3. 過濾出回測期間的數據
        backtest_df = df.loc[df["start_time"] >= self.start_time]
        backtest_df = backtest_df.dropna(axis=0, how="any")

        # 5. 核心日期迴圈
        print(f"-> 策略將在 {len(backtest_df)} 個交易日中運行...")
        row_idx = 0
        for index, row in backtest_df.iterrows():
            self.date_idx_map[row.start_time] = row_idx
            row_idx += 1

            if row_idx % 1000 == 0:
                print(f"finish {row_idx} / {backtest_df.shape[0]}")
            # --- I. 獲取策略決策 ---
            # trade_record = self.get_trade_record(row, self.trade_detail)
            trade_record = self.get_trade_record_by_date(row.start_time)

            trade_svc.build_txn_detail_list_df(row, self.invest_amt, self.guarantee_amt, self.leverage, trade_record,
                                               self.trade_detail)

            # --- II. 模擬交易計算 ---
            # 確認有沒有爆倉
            last_td = self.trade_detail.txn_detail_list[len(self.trade_detail.txn_detail_list) - 1] if len(
                self.trade_detail.txn_detail_list) > 0 else None
            if last_td and ((last_td.units > 0 and Decimal(row.low) < last_td.force_close_offset_price) or (
                    last_td.units < 0 and Decimal(row.high) > last_td.force_close_offset_price)):
                trade_svc.build_txn_detail_list_df(row,
                                                   self.invest_amt,
                                                   self.guarantee_amt,
                                                   self.leverage,
                                                   trade_svc.create_close_trade_record(row.start_time,
                                                                                       last_td.force_close_offset_price,
                                                                                       last_td,
                                                                                       reason=TradeReason(
                                                                                           TradeReasonType.PASSIVE,
                                                                                           "爆倉")),
                                                   self.trade_detail)
                continue

        for txn_detail in self.trade_detail.txn_detail_list:
            df.loc[df['start_time'] == txn_detail.date, 'txn_detail'] = txn_detail

        chart_service.export_trade_point_chart(self.test_name, df, {
            "start_time": self.start_time
            , "end_time": self.end_time
            , "initial_capital": self.initial_capital
            , "product": self.product
            , "leverage": self.leverage
            , "other_args": self.other_args})
