import datetime


DATETIME_FORMAT_NETWORK = "%Y-%m-%d %H:%M:%S"

def format_datetime_old(time: datetime.datetime) -> str:
    return time.strftime("%H:%M:%S")

def format_datetime_network(time: datetime.datetime) -> str:
    return time.strftime(DATETIME_FORMAT_NETWORK)

def read_network_datetime(time: str) -> datetime.datetime:
    return datetime.datetime.strptime(time, DATETIME_FORMAT_NETWORK)