""" The module of helper functions for other core modules.
"""
from strict_rfc3339 import rfc3339_to_timestamp, now_to_rfc3339_localoffset
from datetime import datetime
import os


def rfc3339_to_datetime(rfc3339str):
    return datetime.utcfromtimestamp(
        rfc3339_to_timestamp(rfc3339str))


def current_timestamp():
    return now_to_rfc3339_localoffset()


def joinpath_norm(path, *paths):
    """ os.path.join plus os.path.normpath. Same interface as os.path.join.

    :param path:
    :param paths:
    :return: normalized joined path.
    """
    return os.path.normpath(os.path.join(path, *paths))


def get_relative_path(filepath):
    if filepath[0] == os.sep:
        assert filepath[1] != os.sep, "file must start with '/'!"
        return filepath[1:]
    else:
        return filepath