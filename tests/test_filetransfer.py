""" test script for datajoin.filetransfer.filetransfer.

it's asssumed that datajoin package can be found now, probably by playing with PYTHONPATH.
"""
import itertools
import os
import shutil
import unittest
from copy import deepcopy



import datasmart.core.filetransfer
import datasmart.core.util
from datasmart.core import schemautil
from datasmart.test_util import file_util

class TestFileTransferLocal(unittest.TestCase):

    @classmethod
    def tearDownClass(cls):
        # check git is clean
        datasmart.core.util.check_git_repo_clean()

    @classmethod
    def setUpClass(cls):
        # check git is clean
        datasmart.core.util.check_git_repo_clean()

    def setUp(self):
        config_this = {
            "local_data_dir": "_data",
            "site_mapping_push": [],
            "site_mapping_fetch": [],
            "remote_site_config": {},
            "default_site": {},
            "quiet": True,  # less output.
            "local_fetch_option": "copy"
        }

        self.dirs_to_cleanup = file_util.gen_unique_local_paths(3)
        self.local_data_dir = self.dirs_to_cleanup[0]
        self.default_site_path = self.dirs_to_cleanup[1]
        self.external_site = self.dirs_to_cleanup[2]
        self.subdirs = file_util.gen_filenames(3)
        self.dest_append_prefix = file_util.gen_filenames(3)

        config_this['local_data_dir'] = os.path.abspath(self.local_data_dir)
        config_this['default_site'] = {'local': True, 'path': os.path.abspath(self.default_site_path)}
        config_this_normalized = datasmart.core.filetransfer.FileTransfer.normalize_config(deepcopy(config_this))
        self.assertTrue(os.path.exists(self.local_data_dir))
        shutil.rmtree(self.local_data_dir)
        assert config_this == config_this_normalized
        assert schemautil.validate(datasmart.core.filetransfer.FileTransferConfigSchema.get_schema(), config_this)
        self.filetransfer = datasmart.core.filetransfer.FileTransfer(config_this)

    def test_push(self):
        for x in itertools.product([self.subdirs, None], [True, False], [self.dest_append_prefix, None], [1, 100]):
            subdirs_this, relative, dest_append_prefix, filecount = x
            with self.subTest(subdirs_this=subdirs_this, relative=relative, dest_append_prefix=dest_append_prefix,
                              filecount=filecount):
                self.filelist = file_util.gen_filelist(filecount, abs_path=False)
                file_util.create_dirs_from_dir_list([self.local_data_dir, self.default_site_path])
                self.local_push(subdirs_this=subdirs_this, relative=relative, dest_append_prefix=dest_append_prefix)
                file_util.rm_dirs_from_dir_list([self.local_data_dir, self.default_site_path])

    def test_fetch(self):
        for x in itertools.product([self.subdirs, None], [True, False], [1, 100]):
            subdirs_this, relative, filecount = x
            with self.subTest(subdirs_this=subdirs_this, relative=relative, filecount=filecount):
                self.filelist = file_util.gen_filelist(filecount, abs_path=False)
                file_util.create_dirs_from_dir_list([self.local_data_dir, self.external_site])
                self.local_fetch(subdirs_this=subdirs_this, relative=relative)
                file_util.rm_dirs_from_dir_list([self.local_data_dir, self.external_site])

    def local_fetch(self, subdirs_this=None, relative=True):
        # test local fetch, so create external and local data dir
        # ok. Now time to create files in external.
        file_util.create_files_from_filelist(self.filelist, self.external_site)
        ret = self.filetransfer.fetch(filelist=self.filelist, src_site={'path': self.external_site, 'local': True},
                                      relative=relative,
                                      subdirs=subdirs_this)
        self.check_local_push_fetch_result(True, ret, self.external_site, subdirs_this, relative=relative)
        # check dry run.
        ret2 = self.filetransfer.fetch(filelist=self.filelist, src_site={'path': self.external_site, 'local': True},
                                       relative=relative,
                                       subdirs=subdirs_this, dryrun=True)
        self.assertEqual(ret, ret2)

    def local_push(self, subdirs_this=None, relative=True, dest_append_prefix=None):
        if dest_append_prefix is None:
            dest_append_prefix = ['']
        # test local fetch, so create external and local data dir
        if len(dest_append_prefix) > 1:
            # ok, if dest_append_prefix has more than 2 levels, create all intermediate directories except for last one.
            os.makedirs(os.path.join(*([self.default_site_path] + dest_append_prefix[:-1])))
        # ok. Now time to create files in local data sub dirs.
        file_util.create_files_from_filelist(self.filelist, self.local_data_dir, subdirs_this)

        ret = self.filetransfer.push(filelist=self.filelist, relative=relative, subdirs=subdirs_this,
                                     dest_append_prefix=dest_append_prefix)
        self.check_local_push_fetch_result(False, ret, self.default_site_path, subdirs_this,
                                           relative=relative, dest_append_prefix=dest_append_prefix)
        # check dry run.
        ret2 = self.filetransfer.push(filelist=self.filelist, relative=relative, subdirs=subdirs_this,
                                      dest_append_prefix=dest_append_prefix, dryrun=True)
        self.assertEqual(ret, ret2)

    def check_local_push_fetch_result(self, fetch_flag, ret, external_site,
                                      subdirs_this=None, relative=True, dest_append_prefix=None):
        if subdirs_this is None:
            subdirs_this = []
        if dest_append_prefix is None:
            dest_append_prefix = ['']
        dest_append_prefix = datasmart.core.util.joinpath_norm(*dest_append_prefix)
        # you must be relative path.
        self.assertFalse(os.path.isabs(dest_append_prefix))
        # check return value.
        self.assertTrue(ret['dest']['local'])
        self.assertTrue(ret['src']['local'])
        self.assertEqual(ret['src'], ret['src_actual'])
        self.assertEqual(ret['dest'], ret['dest_actual'])

        local_site_dict = {'local': True,
                           'path': datasmart.core.util.joinpath_norm(os.path.abspath(self.local_data_dir),
                                                                     *subdirs_this)}
        external_site_dict = {'local': True,
                              'path': datasmart.core.util.joinpath_norm(os.path.abspath(external_site))}
        if not fetch_flag:
            external_site_dict['append_prefix'] = dest_append_prefix

        if fetch_flag:
            self.assertEqual(ret['src'], external_site_dict)
            self.assertEqual(ret['dest'], local_site_dict)
        else:
            self.assertEqual(ret['src'], local_site_dict)
            self.assertEqual(ret['dest'], external_site_dict)

        if not fetch_flag:
            self.assertEqual(ret['filelist'], [datasmart.core.util.joinpath_norm(dest_append_prefix,
                                                                                 x if relative else os.path.basename(x))
                                               for x in
                                               self.filelist])
        else:
            self.assertEqual(ret['filelist'], [x if relative else os.path.basename(x) for x in self.filelist])

        for idx, file in enumerate(self.filelist):
            if fetch_flag:
                dest_file_actual = os.path.join(
                    *([self.local_data_dir] + subdirs_this + [file if relative else os.path.basename(file)]))
                src_file_actual = os.path.join(external_site, file)
            else:
                dest_file_actual = os.path.join(external_site, dest_append_prefix,
                                                (file if relative else os.path.basename(file)))
                src_file_actual = os.path.join(*([self.local_data_dir] + subdirs_this + [file]))
            self.assertTrue(os.path.exists(dest_file_actual))
            src_file = os.path.join(ret['src']['path'], self.filelist[idx])
            dest_file = os.path.join(ret['dest']['path'], ret['filelist'][idx])
            self.assertFalse(os.path.isabs(ret['filelist'][idx]))
            self.assertTrue(os.path.samefile(dest_file_actual, dest_file))
            self.assertTrue(os.path.samefile(src_file_actual, src_file))
            self.assertTrue(os.path.normpath(src_file) == src_file)
            self.assertTrue(os.path.normpath(dest_file) == dest_file)
            self.assertFalse(os.path.samefile(src_file, dest_file))

            # check file being the same.
            with open(dest_file, 'rb') as f1, open(src_file, 'rb') as f2:
                self.assertEqual(f1.read(), f2.read())


if __name__ == '__main__':
    unittest.main(failfast=True)
