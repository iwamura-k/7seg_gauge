import datetime


def get_time():
    jst = datetime.timezone(datetime.timedelta(hours=+9), "JST")
    return datetime.datetime.now(jst)


def get_timestamp() -> str:
    now=get_time()
    timestamp = now.strftime('%Y%m%d%H%M%S')
    return timestamp

def to_time_object(timestamp):
    s_format ='%Y%m%d%H%M%S'
    return datetime.datetime.strptime(timestamp, s_format)
