import datetime
from datetime import timezone
from decimal import Decimal
from typing import List

from binance import Client

from com.willy.binance.config.config_util import config_util
from com.willy.binance.dto.binance_kline import BinanceKline
from com.willy.binance.enums.binance_product import BinanceProduct
from com.willy.binance.util import type_util


class BinanceSvc:
    config = config_util("binance.acct.hedgebuy")
    client = Client(config.get("apikey"), config.get("privatekey"))
    enable_trade_detail_log = False
    enable_hedge_trade_plan_log = False
    enable_trade_summary_log = True

    def get_historical_klines(self, binance_product: BinanceProduct, kline_interval=Client.KLINE_INTERVAL_1DAY,
                              start_date: datetime = type_util.str_to_date("20250101"),
                              end_date: datetime = type_util.str_to_date("20250105")) -> List[BinanceKline]:
        klines = self.client.get_historical_klines(binance_product.name, kline_interval,
                                                   int(start_date.timestamp() * 1000),
                                                   int(end_date.timestamp() * 1000))

        self.client.get_avg_price()
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
