from binance import Client, ThreadedWebsocketManager, ThreadedDepthCacheManager

from com.willy.binance.config.config_util import config_util
from com.willy.binance.enum.binance_product import BinanceProduct
from com.willy.binance.service.binance_svc import binance_svc
from com.willy.binance.util import type_util

print(binance_svc().get_historical_klines(BinanceProduct.BTCUSDT, start_date=type_util.str_to_datetime("20251020"),
                                          end_date=type_util.str_to_datetime("20251101")))
