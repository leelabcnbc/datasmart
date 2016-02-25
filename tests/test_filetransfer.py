""" test script for datajoin.filetransfer.filetransfer.

it's asssumed that datajoin package can be found now, probably by playing with PYTHONPATH.
"""
import shutil
import os
from copy import deepcopy
import itertools
import test_util
import datasmart.core.filetransfer
import datasmart.core.util


def check_local_push_fetch_result(fetch_flag, ret, filelist, local_data_dir, external_site, subdirs_this=None,
                                  relative=True):
    if subdirs_this is None:
        subdirs_this = []
    # check return value.
    assert ret['dest']['local']
    assert ret['src']['local']
    for idx, file in enumerate(filelist):
        if fetch_flag:
            dest_file_actual = os.path.join(
                *([local_data_dir] + subdirs_this + [file if relative else os.path.basename(file)]))
            src_file_actual = os.path.join(external_site, file)
        else:
            dest_file_actual = os.path.join(external_site, (file if relative else os.path.basename(file)))
            src_file_actual = os.path.join(*([local_data_dir] + subdirs_this + [file]))
        assert os.path.exists(dest_file_actual)
        src_file = os.path.join(ret['src']['path'], filelist[idx])
        dest_file = os.path.join(ret['dest']['path'], ret['filelist'][idx])
        assert not os.path.isabs(ret['filelist'][idx])
        assert os.path.samefile(dest_file_actual, dest_file)
        assert os.path.samefile(src_file_actual, src_file)
        assert os.path.normpath(src_file) == src_file
        assert os.path.normpath(dest_file) == dest_file
        assert not os.path.samefile(src_file, dest_file)

        # check file being the same.
        with open(dest_file, 'rb') as f1, open(src_file, 'rb') as f2:
            assert f1.read() == f2.read()


def local_fetch(filetransfer, filelist, local_data_dir, external_site, subdirs_this=None, relative=True):
    # test local fetch, so create external and local data dir
    try:
        os.mkdir(local_data_dir)
        os.mkdir(external_site)
        # ok. Now time to create files in external.
        test_util.create_files_from_filelist(filelist, external_site)

        ret = filetransfer.fetch(filelist=filelist, site={'path': external_site, 'local': True}, relative=relative,
                                 subdirs=subdirs_this)
        check_local_push_fetch_result(True, ret, filelist, local_data_dir, external_site, subdirs_this,
                                      relative=relative)
    finally:
        if os.path.exists(local_data_dir):
            shutil.rmtree(local_data_dir)
        if os.path.exists(external_site):
            shutil.rmtree(external_site)


def local_push(filetransfer, filelist, local_data_dir, default_site_path, subdirs_this=None, relative=True):
    # test local fetch, so create external and local data dir
    try:
        os.mkdir(local_data_dir)
        os.mkdir(default_site_path)
        # ok. Now time to create files in local data sub dirs.
        test_util.create_files_from_filelist(filelist, local_data_dir, subdirs_this)

        ret = filetransfer.push(filelist=filelist, relative=relative,
                                subdirs=subdirs_this)
        check_local_push_fetch_result(False, ret, filelist, local_data_dir, default_site_path, subdirs_this,
                                      relative=relative)
    finally:
        if os.path.exists(local_data_dir):
            shutil.rmtree(local_data_dir)
        if os.path.exists(default_site_path):
            shutil.rmtree(default_site_path)


def main_func():
    filetransfer = datasmart.core.filetransfer.FileTransfer()
    config_default = deepcopy(filetransfer.config)

    for i in range(10):
        #  since only local transfer is considered,
        filelist = test_util.gen_filelist(100, abs_path=False)
        local_data_dir = " ".join(test_util.fake.words())
        default_site_path = " ".join(test_util.fake.words())
        external_site = " ".join(test_util.fake.words())
        subdirs = test_util.fake.words()
        config_this = deepcopy(config_default)
        config_this['local_data_dir'] = local_data_dir
        config_this['default_site']['local'] = True
        config_this['default_site']['path'] = default_site_path
        config_this['quiet'] = True  # less output.
        filetransfer_this = datasmart.core.filetransfer.FileTransfer(config_this)
        for x in itertools.product([subdirs, None], [True, False]):
            subdirs_this, relative = x
            local_fetch(filetransfer_this, filelist, local_data_dir, external_site,
                        subdirs_this=subdirs_this, relative=relative)
            local_push(filetransfer_this, filelist, local_data_dir, default_site_path,
                       subdirs_this=subdirs_this, relative=relative)
        print('pass {}'.format(i))


if __name__ == '__main__':
    main_func()
