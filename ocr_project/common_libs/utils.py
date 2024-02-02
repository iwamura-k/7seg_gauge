import datetime


def get_time():
    jst = datetime.timezone(datetime.timedelta(hours=+9), "JST")
    return datetime.datetime.now(jst)


def get_timestamp() -> str:
    now = get_time()
    timestamp = now.strftime('%Y%m%d%H%M%S')
    return timestamp


def to_time_object(timestamp):
    s_format = '%Y%m%d%H%M%S'
    return datetime.datetime.strptime(timestamp, s_format)


def to_time_string(time_object):
    return time_object.strftime('%Y年%m月%d日%H時%M分%S秒')


def parse_time(s):
    temp = s.split("-")
    return int(temp[0]), int(temp[1]), int(temp[2])
