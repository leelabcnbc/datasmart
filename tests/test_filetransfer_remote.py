""" test script for datajoin.filetransfer.filetransfer.

it's asssumed that datajoin package can be found now, probably by playing with PYTHONPATH.
"""
import test_util
import shutil
import os
import itertools
from copy import deepcopy


import datasmart.core.filetransfer
import datasmart.core.util


def check_remote_push_fetch_result(ret_push, ret_fetch, filelist,
                                   local_data_dir, local_cache_dir, subdirs_push=None, subdirs_fetch=None,
                                   relative_push=True, relative_fetch=True, push_prefix="/"):
    """
    :param ret_push:
    :param ret_fetch:
    :param filelist:
    :param local_data_dir:
    :param local_cache_dir:
    :param subdirs_this:
    :param relative:
    :return:
    """
    if subdirs_push is None:
        subdirs_push = []

    if subdirs_fetch is None:
        subdirs_fetch = []

    # check sites' remote/local type.
    assert not ret_push['dest']['local']
    assert ret_push['src']['local']
    assert ret_fetch['dest']['local']
    assert not ret_fetch['src']['local']

    # check that the remote server is kept the same.
    assert ret_push['dest'] == ret_fetch['src']

    # check retrieved result.
    for idx, file in enumerate(filelist):
        # there are the following paths for each file.
        # 1. local_data_dir/subdirs_push/file
        # 2(not checked). {remote_host}:{prefix}/{file | basename} depending on relative_push or not.
        # 3. ret_push['filelist'][idx] should equal {prefix}/{file | basename} (part of 2 after ":")
        #    depending on relative_push or not.
        # 4. ret_fetch['filelist'][idx] should equal
        #    { relative(ret_push['filelist'][idx]) | basename(ret_push['filelist'][idx])}
        #    depending on relative_fetch or not.
        # 5. the fetched file is under local_cache_dir/subdirs_fetch/
        #    { relative(ret_push['filelist'][idx]) | basename(ret_push['filelist'][idx])}
        #    depending on relative_fetch or not.
        #
        # I will check
        # relationship between 1 (file and basename) and 3
        # relationship between 3 and 4
        # also, that the files (filename1 and filename5) are indeed the same.
        # also, 3 and 4 are already normalized.
        # also, 3 is absolute, 4 is relative.

        filebase = os.path.basename(file)
        filename1 = os.path.join(*([local_data_dir] + subdirs_push + [file]))
        filename3 = ret_push['filelist'][idx]
        filename4 = ret_fetch['filelist'][idx]
        filename5 = os.path.join(*([local_cache_dir] + subdirs_fetch + [filename4]))
        # 1 and 3
        assert filename3==os.path.join(push_prefix, file if relative_push else filebase)
        # 3 and 4
        assert filename4 == filename3 if relative_fetch else os.path.basename(filename3)

        # the files (filename1 and filename5) are indeed the same.
        assert os.path.exists(filename1) and os.path.exists(filename5)
        assert not os.path.samefile(filename1, filename5)
        with open(filename1, 'rb') as f1, open(filename5, 'rb') as f2:
            assert f1.read() == f2.read()

        # 3 and 4 are already normalized.
        # 3 is absolute, 4 is relative.
        assert os.path.normpath(filename3)==filename3 and os.path.isabs(filename3)
        assert os.path.normpath(filename4)==filename4 and (not os.path.isabs(filename4))






def remote_push_fetch(filetransfer, filelist, local_data_dir, local_cache_dir, subdirs_push=None, subdirs_fetch=None,
                      relative_push=True, relative_fetch=True):
    # this is combined test of remote push and fetch.
    # I combine them since I can't easily check the files on the server...
    # maybe I can manually check. Well you can run things like ``ls`` on server to get back files...
    # But that's too complicated.

    try:
        os.mkdir(local_data_dir)
        # ok. Now time to create files in local data
        test_util.create_files_from_filelist(filelist, local_data_dir, subdirs_this=subdirs_push)

        # do the push, relative.
        ret_push = filetransfer.push(filelist=filelist, relative=relative_push,subdirs=subdirs_push)

        # do the fetch.
        os.mkdir(local_cache_dir)
        config_old = deepcopy(filetransfer.config)
        config_new = deepcopy(filetransfer.config)
        config_new['local_data_dir'] = local_cache_dir
        filetransfer.set_config(config_new)
        ret_fetch = filetransfer.fetch(
            filelist=ret_push['filelist'],
            src_site=ret_push['dest'], relative=relative_fetch, subdirs=subdirs_fetch)
        check_remote_push_fetch_result(ret_push,
                                       ret_fetch,
                                       filelist, local_data_dir, local_cache_dir,
                                       subdirs_push=subdirs_push, subdirs_fetch=subdirs_fetch,
                                       relative_push=relative_push, relative_fetch=relative_fetch,
                                       push_prefix=config_new['site_config'][
                                           config_new['default_site']['path']]['push_prefix'])
        input("one done.")
    finally:
        filetransfer.set_config(config_old)
        if os.path.exists(local_data_dir):
            shutil.rmtree(local_data_dir)
        if os.path.exists(local_cache_dir):
            shutil.rmtree(local_cache_dir)


def main_func():
    filetransfer = datasmart.core.filetransfer.FileTransfer()
    config_default = deepcopy(filetransfer.config)

    for i in range(1):
        #  since only local transfer is considered,
        filelist = test_util.gen_filelist(100, abs_path=False)
        local_data_dir = " ".join(test_util.fake.words())
        local_cache_dir = " ".join(test_util.fake.words())
        subdirs_push = test_util.fake.words()
        subdirs_fetch = test_util.fake.words()
        config_this = deepcopy(config_default)
        config_this['local_data_dir'] = local_data_dir
        config_this['site_mapping'] = [
            # {
            #     "from":
            #     {
            #         "path": "yimengzh.cnbc.cmu.edu",
            #         "local": False
            #     },
            #     "to":
            #      {
            #         "path": local_cache_dir,
            #         "local": True
            #     }
            # }
        ]
        config_this['default_site']['local'] = False
        config_this['default_site']['path'] = "yimengzh.cnbc.cmu.edu"
        config_this['quiet'] = True
        filetransfer.set_config(config_this)

        # test push & fetch: first add data in local_data_dir, then push, then set ``config_this['local_data_dir']``
        # to local_cache_dir, then fetch data into local_cache_dir, and then compare.
        for x in itertools.product([subdirs_push, None], [subdirs_fetch, None], [True, False], [True, False]):
            subdirs_push_this, subdirs_fetch_this, relative_push_this, relative_fetch_this = x
            print("push rel: {}, fetch rel: {}".format(relative_push_this, relative_fetch_this))
            remote_push_fetch(filetransfer, filelist, local_data_dir, local_cache_dir,
                              subdirs_push=subdirs_push_this, subdirs_fetch=subdirs_fetch_this,
                              relative_push=relative_push_this, relative_fetch=relative_fetch_this)



        print('pass {}'.format(i))


if __name__ == '__main__':
    main_func()
