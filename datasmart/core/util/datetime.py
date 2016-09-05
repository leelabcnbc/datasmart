from datetime import datetime

import pytz
from strict_rfc3339 import rfc3339_to_timestamp, now_to_rfc3339_localoffset

from datasmart.core.util.config import load_config


def rfc3339_to_datetime(rfc3339str):
    return datetime.utcfromtimestamp(
        rfc3339_to_timestamp(rfc3339str))


def current_timestamp():
    return now_to_rfc3339_localoffset()


util_config = load_config(('core', 'util'), filename='config.json', load_json=True)
local_tz = pytz.timezone(util_config['timezone'])


def local_datetime(*args, **kwargs):
    return local_tz.localize(datetime(*args, **kwargs))