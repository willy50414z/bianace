import logging
from datetime import datetime, timezone


def str_date_to_timestamp(yyyymmdd):
    dt = datetime.strptime(yyyymmdd, "%Y%m%d")
    # If you want milliseconds since epoch in UTC
    dt_utc = dt.replace(tzinfo=timezone.utc)
    return int(dt_utc.timestamp() * 1000)


def timestamp_to_datetime(timestamp: int, tz=None):
    try:
        return datetime.fromtimestamp(timestamp, tz=tz)
    except Exception as e:
        logging.error(f"[timestamp_to_datetime]fail,timestamp[{timestamp}]", e)
        raise e


def datetime_to_str(dt: datetime, format="%Y%m%d"):
    return dt.strftime(format)


def str_to_datetime(str):
    return datetime.strptime(str, "%Y%m%d")
