import getpass
import itertools
import os.path
import shutil
import time
import unittest
from copy import deepcopy

import datasmart.core.filetransfer
import datasmart.core.util.util_old
from datasmart.core import schemautil
from datasmart.test_util import file_util

local_map_dir_root = None
remote_dir_root = None


class TestFileTransferRemote(unittest.TestCase):
    @classmethod
    def tearDownClass(cls):
        # check git is clean
        datasmart.core.util.util_old.check_git_repo_clean()

    @classmethod
    def setUpClass(cls):
        # check git is clean
        datasmart.core.util.util_old.check_git_repo_clean()

    def setup_config(self, nas_ip_address, local_data_dir, remote_data_dir, username):
        config_this = {
            "local_data_dir": "_data",
            "site_mapping_push": [],
            "site_mapping_fetch": [],
            "remote_site_config": {},
            "default_site": {},
            "quiet": True,  # less output.
            "local_fetch_option": "copy"
        }
        config_this['local_data_dir'] = os.path.abspath(local_data_dir)
        config_this['site_mapping_push'] = [
            {
                "from":
                    {
                        "path": nas_ip_address,
                        "prefix": datasmart.core.util.util_old.joinpath_norm(remote_dir_root, remote_data_dir),
                        "local": False
                    },
                "to":
                    {
                        "path": datasmart.core.util.util_old.joinpath_norm(local_map_dir_root, remote_data_dir),
                        "local": True
                    }
            }
        ]
        config_this['site_mapping_fetch'] = [
            {
                "from":
                    {
                        "path": nas_ip_address,
                        "prefix": datasmart.core.util.util_old.joinpath_norm(remote_dir_root, remote_data_dir),
                        "local": False
                    },
                "to":
                    {
                        "path": datasmart.core.util.util_old.joinpath_norm(local_map_dir_root, remote_data_dir),
                        "local": True
                    }
            }
        ]
        config_this['remote_site_config'] = {
            nas_ip_address: {
                "ssh_username": username,
                "ssh_port": 22
            }
        }
        config_this['default_site'] = {"path": nas_ip_address,
                                       "prefix": datasmart.core.util.util_old.joinpath_norm(remote_dir_root,
                                                                                            remote_data_dir),
                                       "local": False}
        config_this['quiet'] = True
        config_this['local_fetch_option'] = 'copy'
        config_this_normalized = datasmart.core.filetransfer.FileTransfer.normalize_config(deepcopy(config_this))
        assert config_this == config_this_normalized
        assert schemautil.validate(datasmart.core.filetransfer.FileTransferConfigSchema.get_schema(), config_this)
        self.filetransfer = datasmart.core.filetransfer.FileTransfer(config_this)
        self.assertTrue(os.path.exists(local_data_dir))
        shutil.rmtree(local_data_dir)


    #@unittest.skip("too long")
    def test_all(self):
        global local_map_dir_root
        global remote_dir_root
        username = getpass.getuser()
        nas_ip_address = "localhost"
        numlist = (1, 5, 20)  # test 1 file, 5 files, and 20 files.
        for idx, filecount in enumerate(numlist):
            filelist = file_util.gen_filelist(filecount, abs_path=False)

            self.dirs_to_cleanup = file_util.gen_unique_local_paths(4)


            local_data_dir = self.dirs_to_cleanup[0]
            local_cache_dir = self.dirs_to_cleanup[1]
            remote_data_dir = self.dirs_to_cleanup[2]

            subdirs_push = file_util.gen_filenames(3)
            subdirs_fetch = file_util.gen_filenames(3)
            dest_append_prefix = file_util.gen_filenames(3)

            # ``local_map_dir_root/remote_data_dir`` (or ``remote_dir_root/remote_data_dir`` will be used to save files
            local_map_dir_root = self.dirs_to_cleanup[3]
            remote_dir_root = file_util.gen_unique_local_paths(1)[0]

            # check that all of them are different.
            local_map_dir_root = os.path.abspath(local_map_dir_root)
            remote_dir_root = os.path.abspath(remote_dir_root)
            os.makedirs(local_map_dir_root)
            # remote_dir_root is a symlink
            os.symlink(local_map_dir_root, remote_dir_root)


            self.setup_config(nas_ip_address=nas_ip_address,
                              local_data_dir=local_data_dir,
                              remote_data_dir=remote_data_dir,username=username)

            # create all directories


            # test push & fetch: first add data in local_data_dir, then push, then set ``config_this['local_data_dir']``
            # to local_cache_dir, then fetch data into local_cache_dir, and then compare.
            for x in itertools.product([subdirs_push, None], [subdirs_fetch, None], [True, False], [True, False],
                                       [dest_append_prefix, None], ['copy', 'nocopy'], [True, False], [True, False],
                                       [True, False]):

                subdirs_push_this, subdirs_fetch_this, relative_push_this, \
                relative_fetch_this, dest_append_prefix_this, local_fetch_option, \
                map_push, map_fetch, strip_append_prefix = x

                # filter out incompatible cases with strip_appendix=True.
                if strip_append_prefix and not (dest_append_prefix_this and relative_fetch_this):
                    continue
                with self.subTest(subdirs_push_this=subdirs_push_this, subdirs_fetch_this=subdirs_fetch_this,
                                  relative_push_this=relative_push_this, relative_fetch_this=relative_fetch_this,
                                  dest_append_prefix_this=dest_append_prefix_this,
                                  local_fetch_option=local_fetch_option,
                                  map_push=map_push, map_fetch=map_fetch, strip_append_prefix=strip_append_prefix):


                    self.remote_push_fetch(filelist, local_data_dir, local_cache_dir,
                                           subdirs_push=subdirs_push_this, subdirs_fetch=subdirs_fetch_this,
                                           relative_push=relative_push_this, relative_fetch=relative_fetch_this,
                                           dest_append_prefix=dest_append_prefix_this, nas_ip_address=nas_ip_address,
                                           remote_data_dir=remote_data_dir, local_fetch_option=local_fetch_option,
                                           map_push=map_push, map_fetch=map_fetch,
                                           strip_append_prefix=strip_append_prefix)
                    # time.sleep(2)  # wait for a while for delete to finish.

            self.assertTrue(os.path.exists(local_map_dir_root))
            self.assertTrue(os.path.exists(remote_dir_root))
            shutil.rmtree(local_map_dir_root)
            os.remove(remote_dir_root)

    def remote_push_fetch(self, filelist, local_data_dir, local_cache_dir, subdirs_push=None,
                          subdirs_fetch=None,
                          relative_push=True, relative_fetch=True, dest_append_prefix=None, nas_ip_address='',
                          remote_data_dir='', local_fetch_option='copy', map_fetch=False, map_push=False,
                          strip_append_prefix=True):
        # this is combined test of remote push and fetch.

        if strip_append_prefix:
            self.assertTrue(dest_append_prefix and relative_fetch)

        if dest_append_prefix is None:
            dest_append_prefix = ['']
        remote_append_dir = os.path.join(local_map_dir_root, remote_data_dir, *dest_append_prefix)
        remote_append_dir_root = os.path.join(local_map_dir_root, remote_data_dir)
        # print('root dir: {}'.format(remote_append_dir_root))


        filetransfer = self.filetransfer

        try:
            os.makedirs(remote_append_dir, exist_ok=False)
            os.mkdir(local_data_dir)
            # ok. Now time to create files in local data
            file_util.create_files_from_filelist(filelist, local_data_dir, subdirs_this=subdirs_push)

            config_temp = deepcopy(filetransfer.config)
            if not map_push:
                filetransfer.config['site_mapping_push'] = []

            ret_push = filetransfer.push(filelist=filelist, relative=relative_push,
                                         subdirs=subdirs_push, dest_append_prefix=dest_append_prefix)
            ret_push_1 = filetransfer.push(filelist=filelist, relative=relative_push,
                                           subdirs=subdirs_push, dest_append_prefix=dest_append_prefix, dryrun=True)
            self.assertEqual(ret_push, ret_push_1)
            filetransfer.set_config(config_temp)

            # wait for a while for everything to sync.
            # time.sleep(2)

            # do the fetch.
            os.mkdir(local_cache_dir)
            config_new = deepcopy(filetransfer.config)
            config_new['local_data_dir'] = os.path.abspath(local_cache_dir)
            config_new_normalized = datasmart.core.filetransfer.FileTransfer.normalize_config(deepcopy(config_new))
            assert config_new == config_new_normalized
            assert schemautil.validate(datasmart.core.filetransfer.FileTransferConfigSchema.get_schema(), config_new)
            filetransfer.set_config(config_new)

            if not map_fetch:
                filetransfer.config['site_mapping_fetch'] = []

            if strip_append_prefix:
                assert dest_append_prefix != ['']
                strip_prefix = datasmart.core.util.util_old.joinpath_norm(*dest_append_prefix)
            else:
                strip_prefix = ''

            ret_fetch = filetransfer.fetch(
                filelist=ret_push['filelist'],
                src_site=ret_push['dest'], relative=relative_fetch, subdirs=subdirs_fetch,
                local_fetch_option=local_fetch_option, strip_prefix=strip_prefix)
            ret_fetch_1 = filetransfer.fetch(
                filelist=ret_push['filelist'],
                src_site=ret_push['dest'], relative=relative_fetch, subdirs=subdirs_fetch,
                local_fetch_option=local_fetch_option, strip_prefix=strip_prefix, dryrun=True)
            self.assertEqual(ret_fetch, ret_fetch_1)

            self.check_remote_push_fetch_result(ret_push,
                                                ret_fetch,
                                                filelist, local_data_dir, local_cache_dir,
                                                subdirs_push=subdirs_push, subdirs_fetch=subdirs_fetch,
                                                relative_push=relative_push, relative_fetch=relative_fetch,
                                                dest_append_prefix=dest_append_prefix, nas_ip_address=nas_ip_address,
                                                remote_data_dir=remote_data_dir, local_fetch_option=local_fetch_option,
                                                map_fetch=map_fetch, map_push=map_push,
                                                strip_append_prefix=strip_append_prefix)

            # remove dir
            if dest_append_prefix != ['']:
                self.assertTrue(os.path.exists(remote_append_dir))
                filetransfer.remove_dir(site=ret_push['dest'])
                self.assertFalse(os.path.exists(remote_append_dir))

        finally:
            filetransfer.set_config(config_temp)
            shutil.rmtree(local_data_dir)
            shutil.rmtree(local_cache_dir)
            shutil.rmtree(remote_append_dir_root)
            time.sleep(0.05) # some buffer time

    def check_remote_push_fetch_result(self, ret_push, ret_fetch, filelist,
                                       local_data_dir, local_cache_dir, subdirs_push=None, subdirs_fetch=None,
                                       relative_push=True, relative_fetch=True, dest_append_prefix=None,
                                       nas_ip_address='', remote_data_dir='', local_fetch_option='copy',
                                       map_fetch=False, map_push=False, strip_append_prefix=True):

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

        if strip_append_prefix:
            assert dest_append_prefix and relative_fetch

        if subdirs_push is None:
            subdirs_push = []

        if subdirs_fetch is None:
            subdirs_fetch = []

        if dest_append_prefix is None:
            dest_append_prefix = ['']
        dest_append_prefix = datasmart.core.util.util_old.joinpath_norm(*dest_append_prefix)

        # check that the remote server is kept the same.
        ret_pushdest2 = ret_push['dest'].copy()
        assert 'append_prefix' in ret_pushdest2
        del ret_pushdest2['append_prefix']
        assert ret_pushdest2 == ret_fetch['src']

        from_site = {
            "path": nas_ip_address,
            "prefix": datasmart.core.util.util_old.joinpath_norm(remote_dir_root, remote_data_dir),
            "local": False
        }
        to_site = {
            "path": datasmart.core.util.util_old.joinpath_norm(local_map_dir_root, remote_data_dir),
            "local": True
        }

        from_site_auto = from_site.copy()
        from_site_auto['append_prefix'] = dest_append_prefix
        to_site_auto = to_site.copy()
        to_site_auto['append_prefix'] = dest_append_prefix

        # check site
        assert ret_push['src'] == {'path': datasmart.core.util.util_old.joinpath_norm(os.path.abspath(local_data_dir),
                                                                                      *subdirs_push), 'local': True}
        assert ret_push['src'] == ret_push['src_actual']
        # assert ret_push['src_acutal'] == ret_push['src']
        self.assertEqual(ret_push['dest'],from_site_auto)
        if map_push:
            assert ret_push['dest_actual'] == to_site_auto
        else:
            self.assertEqual(ret_push['dest_actual'], from_site_auto)

        # check site
        assert ret_fetch['src'] == from_site
        if map_fetch:
            assert ret_fetch['src_actual'] == to_site
        else:
            assert ret_fetch['src_actual'] == from_site

        if local_fetch_option == 'nocopy' and map_fetch:
            # there's mapping and I don't want copy.
            assert ret_fetch['dest'] == ret_fetch['src_actual']
        else:
            assert ret_fetch['dest'] == {'path': datasmart.core.util.util_old.joinpath_norm(os.path.abspath(local_cache_dir),
                                                                                            *subdirs_fetch), 'local': True}
        assert ret_fetch['dest_actual'] == ret_fetch['dest']


        # ok. now check the filelist

        # check retrieved result.
        for idx, file in enumerate(filelist):
            # there are the following paths for each file.
            # 1. local_data_dir/subdirs_push/file
            # 2(not checked). {remote_host}:{prefix}/{dest_append_prefix}/{file | basename} depending on relative_push or not.
            # 3. ret_push['filelist'][idx] should equal {dest_append_prefix}/{file | basename} (part of 2 after ":")
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

            filebase = os.path.basename(file)
            filename1 = os.path.join(*([local_data_dir] + subdirs_push + [file]))
            filename2 = os.path.join(local_map_dir_root, remote_data_dir, dest_append_prefix, file if relative_push else filebase)
            filename3 = ret_push['filelist'][idx]
            filename4 = ret_fetch['filelist'][idx]
            if not (local_fetch_option == 'nocopy' and map_fetch):
                filename5 = os.path.join(*([local_cache_dir] + subdirs_fetch + [filename4]))
            else:
                # use the one on remote site.
                filename5 = os.path.join(remote_dir_root, remote_data_dir, filename4)
            # 1 and 3

            assert filename3 == datasmart.core.util.util_old.joinpath_norm(dest_append_prefix,
                                                                           file if relative_push else filebase)
            # 3 and 4
            if not (local_fetch_option == 'nocopy' and map_fetch):
                if not strip_append_prefix:
                    self.assertEqual(filename4, filename3 if relative_fetch else filebase)
                else:  # this implies relative fetch already
                    self.assertTrue(relative_fetch)
                    self.assertEqual(filename4, file if relative_push else filebase)
            else:
                self.assertEqual(filename4, filename3)

            # 4 and 5 should be the same, and 2 and 3 should be the same
            assert os.path.samefile(filename2, os.path.join(remote_dir_root, remote_data_dir, filename3))
            if not (local_fetch_option == 'nocopy' and map_fetch):
                assert os.path.samefile(filename5, os.path.join(local_cache_dir, *subdirs_fetch, filename4))
            else:
                assert os.path.samefile(filename5, os.path.join(remote_dir_root, remote_data_dir, filename3))

            # the files (filename1, filename2, and filename5) are indeed the same.
            self.assertTrue(os.path.exists(filename1))
            self.assertTrue(os.path.exists(filename2))
            self.assertTrue(os.path.exists(filename5))
            assert not os.path.samefile(filename1, filename5)
            assert not os.path.samefile(filename1, filename2)
            if not (local_fetch_option == 'nocopy' and map_fetch):
                assert not os.path.samefile(filename2, filename5)
            else:
                assert os.path.samefile(filename2, filename5)
            with open(filename1, 'rb') as f1, open(filename5, 'rb') as f2:
                assert f1.read() == f2.read()
            with open(filename1, 'rb') as f1, open(filename2, 'rb') as f2:
                assert f1.read() == f2.read()

            # 3 and 4 are already normalized are relative.
            assert os.path.normpath(filename3) == filename3 and (not os.path.isabs(filename3))
            assert os.path.normpath(filename4) == filename4 and (not os.path.isabs(filename4))


if __name__ == '__main__':
    unittest.main(failfast=True)
