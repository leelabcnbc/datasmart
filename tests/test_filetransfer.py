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
from datasmart.core import schemautil
import random

def check_local_push_fetch_result(fetch_flag, ret, filelist, local_data_dir, external_site, subdirs_this=None,
                                  relative=True, dest_append_prefix=None):
    if subdirs_this is None:
        subdirs_this = []
    if dest_append_prefix is None:
        dest_append_prefix = ['']
    dest_append_prefix = datasmart.core.util.joinpath_norm(*dest_append_prefix)
    # you must be relative path.
    assert not (os.path.isabs(dest_append_prefix))
    # check return value.
    assert ret['dest']['local']
    assert ret['src']['local']
    assert ret['src'] == ret['src_actual']
    assert ret['dest'] == ret['dest_actual']

    local_site_dict = {'local': True,
                       'path': datasmart.core.util.joinpath_norm(os.path.abspath(local_data_dir), *subdirs_this)}
    external_site_dict = {'local': True,
                          'path': datasmart.core.util.joinpath_norm(os.path.abspath(external_site))}
    if not fetch_flag:
        external_site_dict['append_prefix'] = dest_append_prefix

    if fetch_flag:
        assert ret['src'] == external_site_dict
        assert ret['dest'] == local_site_dict
    else:
        assert ret['src'] == local_site_dict
        assert ret['dest'] == external_site_dict

    if not fetch_flag:
        assert ret['filelist'] == [datasmart.core.util.joinpath_norm(dest_append_prefix,
                                                                     x if relative else os.path.basename(x)) for x in
                                   filelist]
    else:
        assert ret['filelist'] == [x if relative else os.path.basename(x) for x in filelist]

    for idx, file in enumerate(filelist):
        if fetch_flag:
            dest_file_actual = os.path.join(
                *([local_data_dir] + subdirs_this + [file if relative else os.path.basename(file)]))
            src_file_actual = os.path.join(external_site, file)
        else:
            dest_file_actual = os.path.join(external_site, dest_append_prefix,
                                            (file if relative else os.path.basename(file)))
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

        ret = filetransfer.fetch(filelist=filelist, src_site={'path': external_site, 'local': True}, relative=relative,
                                 subdirs=subdirs_this)
        check_local_push_fetch_result(True, ret, filelist, local_data_dir, external_site, subdirs_this,
                                      relative=relative)
        # check dry run.
        ret2 = filetransfer.fetch(filelist=filelist, src_site={'path': external_site, 'local': True}, relative=relative,
                                  subdirs=subdirs_this, dryrun=True)
        assert ret == ret2
    finally:
        if os.path.exists(local_data_dir):
            shutil.rmtree(local_data_dir)
        if os.path.exists(external_site):
            shutil.rmtree(external_site)


def local_push(filetransfer, filelist, local_data_dir, default_site_path, subdirs_this=None, relative=True,
               dest_append_prefix=None):
    if dest_append_prefix is None:
        dest_append_prefix = ['']
    # test local fetch, so create external and local data dir
    try:
        os.mkdir(local_data_dir)
        os.mkdir(default_site_path)
        if len(dest_append_prefix) > 1:
            # ok, if dest_append_prefix has more than 2 levels, then create all intermediate directories except for last one.
            os.makedirs(os.path.join(*([default_site_path] + dest_append_prefix[:-1])))
        # ok. Now time to create files in local data sub dirs.
        test_util.create_files_from_filelist(filelist, local_data_dir, subdirs_this)

        ret = filetransfer.push(filelist=filelist, relative=relative, subdirs=subdirs_this,
                                dest_append_prefix=dest_append_prefix)
        check_local_push_fetch_result(False, ret, filelist, local_data_dir, default_site_path, subdirs_this,
                                      relative=relative, dest_append_prefix=dest_append_prefix)
        # check dry run.
        ret2 = filetransfer.push(filelist=filelist, relative=relative, subdirs=subdirs_this,
                                 dest_append_prefix=dest_append_prefix, dryrun=True)
        assert ret == ret2

        # remove dir
        if dest_append_prefix != ['']:
            assert os.path.exists(os.path.join(default_site_path, *dest_append_prefix))
            filetransfer.remove_dir(site=ret['dest'])
            assert not os.path.exists(os.path.join(default_site_path, *dest_append_prefix))

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
        filelist = test_util.gen_filelist(random.choice([100,1]), abs_path=False)
        local_data_dir = " ".join(test_util.gen_filenames(3))
        default_site_path = " ".join(test_util.gen_filenames(3))
        external_site = " ".join(test_util.gen_filenames(3))
        subdirs = test_util.gen_filenames(3)
        dest_append_prefix = test_util.gen_filenames(3)
        config_this = deepcopy(config_default)
        config_this['local_data_dir'] = local_data_dir
        config_this['default_site'] = {'local': True, 'path': default_site_path}
        config_this['quiet'] = True  # less output.
        assert schemautil.validate(datasmart.core.filetransfer.FileTransferConfigSchema.get_schema(), config_this)
        filetransfer_this = datasmart.core.filetransfer.FileTransfer(config_this)
        for x in itertools.product([subdirs, None], [True, False], [dest_append_prefix, None]):
            subdirs_this, relative, dest_append_prefix_this = x
            local_fetch(filetransfer_this, filelist, local_data_dir, external_site,
                        subdirs_this=subdirs_this, relative=relative)
            local_push(filetransfer_this, filelist, local_data_dir, default_site_path,
                       subdirs_this=subdirs_this, relative=relative, dest_append_prefix=dest_append_prefix_this)
        print('pass {}'.format(i))


if __name__ == '__main__':
    main_func()
