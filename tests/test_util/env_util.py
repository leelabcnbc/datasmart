"""common methods for setting up a test"""

from unittest import TestCase
import os.path
import shutil
import pymongo
from . import file_util

def setup_db(cls_obj: TestCase, table_path: tuple):
    cls_obj.db_client = pymongo.MongoClient()
    assert len(table_path) == 2, "must be a valid table path for MongoDB!"
    cls_obj.collection_client = cls_obj.db_client[table_path[0]][table_path[1]]


def teardown_db(cls_obj: TestCase):
    cls_obj.collection_client.drop()
    cls_obj.db_client.close()


def setup_local_config(config_path: tuple, config_text: str, first_time: bool = True):
    """ setup local config file for a core module / action.

    :param config_path: config_path for the core module / action.
    :param config_text: content of the config file.
    :param first_time: whether this is the first time setting up any local config. If True, local config directory
        ``config`` cannot exist beforehand. Set this to True for first config file, and setting it to False for others.
    :return:
    """
    if first_time:
        os.makedirs("config")
    assert os.path.exists("config")
    subdir = os.path.join('config', *config_path)
    os.makedirs(subdir)
    with open(os.path.join(subdir, "config.json"), "wt") as f:
        f.write(config_text)


def setup_remote_site(subdirs_to_create=None):
    """ setup a remote site locally in localhost, local dir.
    :param subdirs_to_create: None or ('foo','bar') and a subdirectory 'foo/bar' will be created
        under the local remote site
    :return:
    """
    remote_dir_root = os.path.abspath(file_util.gen_unique_local_paths(1)[0])
    site = {
        "path": "localhost",
        "prefix": remote_dir_root,
        "local": False
    }
    os.makedirs(remote_dir_root)
    if subdirs_to_create is not None:
        os.makedirs(os.path.join(remote_dir_root, *subdirs_to_create))

    return site


def teardown_remote_site(site):
    shutil.rmtree(site['prefix'])


def teardown_local_config():
    shutil.rmtree("config")
