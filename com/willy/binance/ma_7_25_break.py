import datetime
from zoneinfo import ZoneInfo

from binance import Client

from com.willy.binance.config.config_util import config_util
from com.willy.binance.enums.binance_product import BinanceProduct
from com.willy.binance.service import trade_svc, telegram_svc
from com.willy.binance.strategy.moving_average_strategy import MovingAverageStrategy
from com.willy.binance.util import type_util

maStrategy = MovingAverageStrategy("ma_with_ma25_2504_061", type_util.str_to_datetime("2025-04-01T00:00:00Z"),
                                   type_util.str_to_datetime("2025-11-30T00:00:00Z"), 50000
                                   , BinanceProduct.BTCUSDT, 20, {"level_amt_change": 1, "dca_levels": 5})
config = config_util("linebot")
line_user_id = config.get("userid_willy")


def lambda_handler(event, context):
    now_utc_time = datetime.datetime.now().astimezone(ZoneInfo("UTC"))

    trade_record = maStrategy.get_trade_record_by_date(now_utc_time)

    if trade_record:
        data_fetch_start = now_utc_time - maStrategy.lookback_tickets
        df = maStrategy.binance_svc.get_klines(maStrategy.product, Client.KLINE_INTERVAL_15MINUTE, data_fetch_start,
                                               now_utc_time)
        trade_svc.build_txn_detail_list_df(df.iloc[-1], maStrategy.invest_amt, maStrategy.guarantee_amt,
                                           maStrategy.leverage,
                                           trade_record,
                                           maStrategy.trade_detail)
        print(maStrategy.trade_detail)
        telegram_svc.push_message(message=maStrategy.trade_detail)
    else:
        telegram_svc.push_message(message=
                                  f"datetime[{type_util.datetime_to_str(datetime.datetime.now(), "%Y/%m/%d %H:%M:%S")}] not trigger trade")

    return {
        'statusCode': 200,
        'body': 'Hello from Lambda Container!'
    }
