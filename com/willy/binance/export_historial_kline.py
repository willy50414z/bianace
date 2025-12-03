from binance import Client

from com.willy.binance.enums.binance_product import BinanceProduct
from com.willy.binance.service.binance_svc import BinanceSvc
from com.willy.binance.util import type_util

if __name__ == '__main__':
    binance_svc = BinanceSvc()
    kline_interval = Client.KLINE_INTERVAL_15MINUTE
    product = BinanceProduct.BTCUSDT
    klines_df = binance_svc.get_historical_klines_df(product, kline_interval,
                                                     type_util.str_to_datetime("2020-01-01T00:00:00Z"),
                                                     type_util.str_to_datetime("2025-11-30T00:00:00Z"))
    # # print("====BEFORE====")
    # # print(klines_df)
    klines_df.to_csv(f'E:/code/binance/data/{product.name}_{kline_interval}.csv', index=False)

    # df_loaded = pd.read_csv('/data/BTCUSDT_4h.csv')
    # print("====AFTER====")
    # print(df_loaded)
