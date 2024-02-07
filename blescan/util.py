import datetime
from typing import Union, Any


DATETIME_FORMAT_NETWORK = "%Y-%m-%d %H:%M:%S"

def format_datetime_old(time: datetime.datetime) -> str:
    return time.strftime("%H:%M:%S")

def format_datetime_network(time: datetime.datetime) -> str:
    return time.strftime(DATETIME_FORMAT_NETWORK)

def read_network_datetime(time: str) -> datetime.datetime:
    return datetime.datetime.strptime(time, DATETIME_FORMAT_NETWORK)

def float_or_else(value: str, default: Any = None) -> Union[float,Any]:
    """
    Cast a string value to a float if possible. If not, return None
    """
    try:
        return float(value)
    except ValueError:
        return default
    
def byte_to_hex(byte_array) -> str:
    return ''.join('{:02x}'.format(_) for _ in byte_array)
    