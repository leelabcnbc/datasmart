""" The module of helper functions for other core modules.
"""
from strict_rfc3339 import rfc3339_to_timestamp, now_to_rfc3339_localoffset
from datetime import datetime
import os
import json
import pkgutil
from .. import global_config
# removed for compatibility with readthedocs.
# from typing import Union

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

#def load_config(module_name: tuple, filename='config.json', load_json=True) -> Union[dict,str]:
def load_config(module_name: tuple, filename='config.json', load_json=True):
    """ load the config file for this module.

    It will perform the following steps:

    1. get the config file ``config/{os.sep.join(module_name)}/config.json``, where ``/`` is ``\`` for Windows,
       under the directory consisting the invoked Python script.
    2. if the above step fails, load the default one provided by the module.


    :param filename: which file to load. by default, ``config.json``.
    :param module_name: module name as a list of strings, "AA.BB" is represented as ``["AA","BB"]``
    :param load_json: whether parse the string as JSON or not.
    :return: the JSON object of the module config file, or the raw string.
    """
    path_list = (global_config['project_root'], 'config') + module_name + (filename,)
    config_path = os.path.join(*path_list)
    if os.path.exists(config_path):
        with open(config_path, 'rt') as config_stream:
            if load_json:
                config = json.load(config_stream)
            else:
                config = config_stream.read()
    else:
        # step 2. load default config
        config = pkgutil.get_data(
            global_config['root_package_spec'] + '.config.' + '.'.join(module_name), filename).decode()
        if load_json:
            config = json.loads(config)
    return config