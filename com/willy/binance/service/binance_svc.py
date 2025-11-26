import datetime
from datetime import timezone
from decimal import Decimal
from typing import List, Optional

import pandas as pd
from binance import Client
from pandas import DataFrame

from com.willy.binance.config.config_util import config_util
from com.willy.binance.dto.acct_dto import AcctDto, AcctBalance
from com.willy.binance.dto.binance_kline import BinanceKline
from com.willy.binance.dto.time_series_dto import TimeSeriesDto
from com.willy.binance.enums.binance_product import BinanceProduct
from com.willy.binance.enums.commission_order import CommissionOrder
from com.willy.binance.enums.currency import Currency
from com.willy.binance.enums.futures_account_info import FuturesAccountInfo
from com.willy.binance.enums.position_info import PositionInfo
from com.willy.binance.enums.transfer_type import TransferType
from com.willy.binance.util import type_util


class BinanceSvc:
    config = config_util("binance.acct.hedgebuy")

    client = Client(config.get("apikey"), config.get("privatekey"))

    def get_historical_klines(self, binance_product: BinanceProduct, kline_interval=Client.KLINE_INTERVAL_1DAY,
                              start_date: datetime = type_util.str_to_date("20250101"),
                              end_date: datetime = type_util.str_to_date("20250105")) -> List[BinanceKline]:
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

    def parse_datetime_row(self, row):
        row['start_time'] = type_util.timestamp_to_datetime(row['start_time'] // 1000, tz=timezone.utc)
        row['end_time'] = type_util.timestamp_to_datetime(row['end_time'] // 1000, tz=timezone.utc)
        return row

    def acct(self):
        acct_dto = AcctDto()
        for balance in self.client.get_account()["balances"]:
            if float(balance["free"]) > 0 or float(balance["locked"]) > 0:
                acct_dto.balances.append(
                    AcctBalance(balance["asset"], float(balance["free"]), float(balance["locked"])))

        return acct_dto

    def get_historical_klines_df(self, binance_product: BinanceProduct, kline_interval=Client.KLINE_INTERVAL_1DAY,
                                 start_date: datetime = type_util.str_to_date("20250101"),
                                 end_date: datetime = type_util.str_to_date("20250105")) -> DataFrame:
        klines = self.client.get_historical_klines(binance_product.name, kline_interval,
                                                   int(start_date.timestamp() * 1000),
                                                   int(end_date.timestamp() * 1000))
        selected_fields = [[row[i] for i in (0, 1, 2, 3, 4, 5, 6, 8)] for row in klines]
        df = pd.DataFrame(selected_fields,
                          columns=['start_time', 'open', 'high', 'low', 'close', 'vol', 'end_time', 'number_of_trade'])
        df = df.apply(self.parse_datetime_row, axis=1)
        df = df.astype(
            {'open': float, 'high': float, 'low': float, 'close': float, 'vol': float, 'number_of_trade': float})
        return df

    def append_ma(self, kline_df: DataFrame, interval: int):
        kline_df['ma' + str(interval)] = kline_df['close'].rolling(window=interval, min_periods=interval).mean().round(
            2)

    def get_close_ma(self, binance_product: BinanceProduct, kline_interval=Client.KLINE_INTERVAL_1DAY,
                     start_date: datetime = type_util.str_to_datetime("2025-11-10T00:00:00Z"),
                     end_date: datetime = type_util.str_to_datetime("2025-11-10T01:00:00Z"), interval: int = 7):
        klines = self.get_historical_klines(binance_product, kline_interval, start_date, end_date)
        return self.calc_close_ma(klines, interval)

    def calc_close_ma(self, klines: List[BinanceKline], interval: int = 7) -> List[TimeSeriesDto]:
        df = pd.DataFrame({
            'time': [kline.start_time for kline in klines],
            'close': [kline.close for kline in klines]
        })
        df['time'] = pd.to_datetime(df['time'])
        df = df.sort_values('time').reset_index(drop=True)
        df['avg_price'] = df['close'].astype(float).rolling(window=interval, min_periods=interval).mean()

        # 將結果轉換為 List[TimeSeriesDto]
        dtos: List[TimeSeriesDto] = [
            TimeSeriesDto(date=t, value=ap)
            for t, ap in zip(df['time'], df['avg_price'])
        ]
        return dtos

    def universal_transfer(self, type: TransferType, asset: Currency, amount=0.0):
        """

        Args:
            type:
                MAIN_UMFUTURE: 現貨到U本位
                UMFUTURE_MAIN: U本位到現貨
            asset:
            amount:

        Returns:

        """
        try:
            result = self.client.universal_transfer(
                type=type.name,  # UMFUTURE_MAIN 表示從 U 本位合約轉到現貨
                asset=asset.name,  # 要轉移的資產
                amount=amount  # 轉移數量（字串格式）
            )
            return result
        except Exception as e:
            print(f"轉帳失敗: {e}")

    def get_account_info(self) -> FuturesAccountInfo:
        """取得完整帳戶資訊"""
        try:
            account_data = self.client.futures_account()
            return FuturesAccountInfo.from_api_response(account_data)
        except Exception as e:
            raise Exception(f"取得帳戶資訊失敗: {e}")

    def get_positions(self, symbol: Optional[str] = None) -> List[PositionInfo]:
        """
        取得持有倉位
        參數:
            symbol: 指定交易對（可選）
        """
        try:
            if symbol:
                position_data = self.client.futures_position_information(symbol=symbol)
            else:
                position_data = self.client.futures_position_information()

            # 過濾出有持倉的
            positions = [
                PositionInfo.from_api_response(pos)
                for pos in position_data
                if float(pos['positionAmt']) != 0
            ]

            return positions
        except Exception as e:
            raise Exception(f"取得倉位失敗: {e}")

    def get_open_orders(self, symbol: Optional[str] = None) -> List[CommissionOrder]:
        """
        取得當前委託單
        參數:
            symbol: 指定交易對（可選）
        """
        try:
            if symbol:
                orders_data = self.client.futures_get_open_orders(symbol=symbol)
            else:
                orders_data = self.client.futures_get_open_orders()

            orders = [CommissionOrder.from_api_response(order) for order in orders_data]
            return orders
        except Exception as e:
            raise Exception(f"取得委託單失敗: {e}")


if __name__ == '__main__':
    service = BinanceSvc()
    service.universal_transfer(TransferType.MAIN_UMFUTURE, Currency.USDC, 0.2)
    account_info = service.get_account_info()
    print(account_info)

    # 取得所有持倉（使用獨立方法）
    positions = service.get_positions()
    print(positions)

    # 取得特定交易對的持倉
    # btc_positions = service.get_positions(symbol='BTCUSDT')

    # 取得所有委託單
    orders = service.get_open_orders()
    print(orders)
    # print(binanceSvc.get_close_ma(BinanceProduct.BTCUSDT, Client.KLINE_INTERVAL_15MINUTE,
    #                               type_util.str_to_datetime("2025-11-10T00:00:00Z"),
    #                               type_util.str_to_datetime("2025-11-10T05:00:00Z"), 7))
