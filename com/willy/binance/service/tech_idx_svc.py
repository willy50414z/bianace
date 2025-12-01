import pandas as pd


def append_ma(kline_df: pd.DataFrame, interval: int):
    kline_df['ma' + str(interval)] = kline_df['close'].rolling(window=interval, min_periods=interval).mean().round(
        2)
