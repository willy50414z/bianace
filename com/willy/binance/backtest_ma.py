from com.willy.binance.enums.binance_product import BinanceProduct
from com.willy.binance.strategy.moving_average_strategy import MovingAverageStrategy
from com.willy.binance.util import type_util

if __name__ == '__main__':
    MovingAverageStrategy("ma_with_ma25_2508", type_util.str_to_datetime("2025-04-01T00:00:00Z"),
                          type_util.str_to_datetime("2025-11-30T17:00:00Z"), 10000
                          , BinanceProduct.BTCUSDT, 20, {"level_amt_change": 1, "dca_levels": 5}).run_backtest()
