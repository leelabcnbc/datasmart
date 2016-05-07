""" The module of helper functions for other core modules.
"""
from strict_rfc3339 import rfc3339_to_timestamp, now_to_rfc3339_localoffset
from datetime import datetime
import os
import json
import pkgutil
import pytz
from .. import global_config
import subprocess
import unicodedata


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
    s = os.path.normpath(os.path.join(path, *paths))
    assert s == os.path.normpath(s)
    # make sure unique unicode normalization.
    check_unique_unicode_normalization(s)
    return s


def normalize_filelist_relative(filelist: list, prefix='') -> list:
    """ normalize a list of relative file paths, and check that paths are well-behaved.

    :param filelist: a list of relative file paths
    :param prefix: an optional preffix
    :return: same file list, with paths normalized.
    """
    assert len(filelist) > 0

    ret_filelist = [joinpath_norm(prefix, p) for p in filelist]
    for p in ret_filelist:
        assert '\n' not in p, 'LF should not exist in file name!'
        assert '\r' not in p, 'CR should not exist in file name!'
        assert '\0' not in p, 'NULL should not exist in file name!'
        assert os.path.normpath(p) == p, "should be already normalized!"
        assert p.strip() == p, "no spaces around filename! this is good for your sanity."
        assert not os.path.isabs(p), "file paths are all relative"
        b = os.path.basename(p)
        assert '/' not in b, 'directory separator should not exist in file name!'
        assert b and (b != '.') and (b != '..'), "no trival file name like empty, ., or ..!"
    return ret_filelist

# this is uncommented due to readthedocs' poor support of Python 3.5 features a while ago.
# def load_config(module_name: tuple, filename='config.json', load_json=True) -> Union[dict,str]:
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
    path_list_global = (os.path.expanduser('~'), '.datasmart', 'config') + module_name + (filename,)
    config_path_global = os.path.join(*path_list_global)
    if os.path.exists(config_path):
        # step 1. load config in current project.
        with open(config_path, 'rt', encoding='utf-8') as config_stream:
            if load_json:
                config = json.load(config_stream)
            else:
                config = config_stream.read()
    elif os.path.exists(config_path_global):
        # step 2. load config in ~/.datasmart
        with open(config_path_global, 'rt', encoding='utf-8') as config_stream:
            if load_json:
                config = json.load(config_stream)
            else:
                config = config_stream.read()
    else:
        # step 3. load default config
        config = pkgutil.get_data(
            global_config['root_package_spec'] + '.config.' + '.'.join(module_name), filename).decode()
        if load_json:
            config = json.loads(config)
    return config


util_config = load_config(('core', 'util'), filename='config.json', load_json=True)
local_tz = pytz.timezone(util_config['timezone'])


def local_datetime(*args, **kwargs):
    return local_tz.localize(datetime(*args, **kwargs))


def get_git_repo_url(repopath):
    return subprocess.check_output(['git', 'ls-remote', '--get-url', 'origin'],
                                   cwd=repopath).decode().strip()


def get_git_repo_hash(repopath):
    return subprocess.check_output(['git', 'rev-parse', '--verify', 'HEAD'],
                                   cwd=repopath).decode().strip()


def check_git_repo_clean(repopath=None):
    if repopath is None:
        # from <http://stackoverflow.com/questions/957928/is-there-a-way-to-get-the-git-root-directory-in-one-command>
        repopath = subprocess.check_output(['git', 'rev-parse', '--show-toplevel']).decode().strip()
        print(repopath)
    git_status_output = subprocess.check_output(['git', 'status', '--porcelain'],
                                                cwd=repopath).decode().strip()
    assert not git_status_output, "the repository must be clean!"
    return True

# config['cortex_expt_repo_path']
#     cortex_expt_repo_url =
#


def check_unique_unicode_normalization(s: str) -> None:
    assert s == unicodedata.normalize('NFC', s) == unicodedata.normalize('NFD', s), "unique normalization must exist!"
