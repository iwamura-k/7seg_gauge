import datetime


def get_timestamp() -> str:
    jst = datetime.timezone(datetime.timedelta(hours=+9), "JST")
    now = datetime.datetime.now(jst)
    timestamp = now.strftime('%Y%m%d%H%M%S')
    return timestamp