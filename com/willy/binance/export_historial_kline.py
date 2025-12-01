import pandas as pd
from binance import Client

from com.willy.binance.enums.binance_product import BinanceProduct
from com.willy.binance.service.binance_svc import BinanceSvc
from com.willy.binance.util import type_util

if __name__ == '__main__':
    binance_svc = BinanceSvc()
    klines_df = binance_svc.get_historical_klines_df(BinanceProduct.BTCUSDT, Client.KLINE_INTERVAL_8HOUR,
                                                     type_util.str_to_datetime("2025-08-01T00:00:00Z"),
                                                     type_util.str_to_datetime("2025-11-12T00:00:00Z"))
    # # print("====BEFORE====")
    # # print(klines_df)
    klines_df.to_csv('E:/code/binance/data/BTCUSDT_8h.csv', index=False)

    df_loaded = pd.read_csv('/data/BTCUSDT_4h.csv')
    print("====AFTER====")
    print(df_loaded)
