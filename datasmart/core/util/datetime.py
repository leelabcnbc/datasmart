from datetime import datetime

import pytz
from strict_rfc3339 import rfc3339_to_timestamp, validate_rfc3339

from datasmart.core.util.config import load_config

util_config = load_config(('core', 'util'), filename='config.json', load_json=True)
local_tz = pytz.timezone(util_config['timezone'])


# datetime: naive, zone unspecified.
# datetime_utc: some datetime with tzinfo guranteed to be utc
# datetime_local: some datetime with tzinfo
# rfc3339: any RFC 3339
# rfc3339_utc: rfc 3339 with guaranteed +00:00 in the end.
# rfc3339_local rfc 3339 with offset defined by some tz (maybe +00:00 as well if tz is utc).

# so datetime_utc is a datetime_local
# rfc3339_utc is a rfc3339_local

def datetime_local_to_rfc3339_local(dt: datetime):
    assert dt.tzinfo is not None
    rfc3339_local = dt.replace(microsecond=0).isoformat()
    assert validate_rfc3339(rfc3339_local)
    return rfc3339_local


def datetime_local_to_rfc3339_utc(dt: datetime):
    assert dt.tzinfo is not None
    rfc3339_utc = dt.astimezone(pytz.utc).replace(microsecond=0).isoformat()
    assert validate_rfc3339(rfc3339_utc)
    return rfc3339_utc


def datetime_to_datetime_local(dt, is_dst=None):
    """converts an naive dt to local dt, basically getting the correct offset"""
    # `is_dst=None` make sure it will crash when dealing with ambiguous time.
    return local_tz.localize(dt, is_dst=is_dst)


def datetime_to_datetime_utc(dt, is_dst=None):
    """add utc info to dt"""
    return pytz.utc.localize(dt, is_dst=is_dst)


def rfc3339_to_datetime(rfc3339str):
    """returns a naive UTC datetime object representing the given rfc3339 timestamp"""
    return datetime.utcfromtimestamp(
        rfc3339_to_timestamp(rfc3339str))


def now_rfc3339_local():
    """return current time, in RFC3339 format, and zone of local_tz"""
    rfc3339_local = pytz.utc.localize(datetime.utcnow()).astimezone(local_tz).replace(microsecond=0).isoformat()
    # for simplicity, the microsecond part is always truncated, since Mongo may not save them in same resolution
    assert validate_rfc3339(rfc3339_local)
    return rfc3339_local


def now_rfc3339_utc():
    """return current time, in RFC3339 format, and UTC"""
    rfc3339_utc = pytz.utc.localize(datetime.utcnow()).replace(microsecond=0).isoformat()
    assert validate_rfc3339(rfc3339_utc)
    return rfc3339_utc
