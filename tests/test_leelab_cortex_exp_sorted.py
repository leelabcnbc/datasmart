import unittest
from datasmart.actions.leelab.cortex_exp_sorted import CortexExpSortedAction, CortexExpSortedSchemaJSL
import unittest.mock as mock
from test_util import file_util
from test_util.mock_util import MockNames
import os
import shutil
import pymongo
import json
from functools import partial
import random
from datasmart.core.util import joinpath_norm
import getpass
from datasmart.core import schemautil
from datasmart.core import util
import strict_rfc3339
from bson import ObjectId
from copy import deepcopy


class LeelabCortexExpSortedAction(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # link to pymongo
        cls.db_client = pymongo.MongoClient()
        cls.collection_client = cls.db_client['leelab']['cortex_exp_sorted']
        assert not os.path.exists("config")
        os.makedirs("config/core/filetransfer")
        cls.local_save_dir = '_data'  # this is the one used in the filetransfer config template.
        cls.collection_client_raw = cls.db_client['temp']['temp']

    def setUp(self):
        self.git_url = 'http://git.example.com'
        self.git_hash = '0000000000000000000000000000000000000000'
        self.git_repo_path = " ".join(file_util.gen_filenames(3))
        self.savepath = " ".join(file_util.gen_filenames(3))
        self.assertNotEqual(self.git_repo_path, self.savepath)  # should be (almost) always true
        self.temp_dict = {}
        self.mock_function = partial(LeelabCortexExpSortedAction.input_mock_function, instance=self)
        self.assertFalse(os.path.exists(self.savepath))
        self.assertFalse(os.path.exists('query_template.py'))
        self.assertFalse(os.path.exists('prepare_result.p'))

        # create git_repo_path.
        os.makedirs(self.git_repo_path)
        with open(os.path.join(self.git_repo_path, 'SAC_batch_summer.tar.gz'), 'wt') as f:
            f.close()
        with open(os.path.join(self.git_repo_path, 'spikesort.tar.gz'), 'wt') as f:
            f.close()

        self.remote_dir_root = os.path.abspath(" ".join(file_util.gen_filenames(3)))
        filelist = file_util.gen_filelist(100, abs_path=False)
        self.filelist_nev = [f + '.nev' for f in filelist[:50]]
        self.filelist_nonev = filelist[50:]
        for f in self.filelist_nonev:
            self.assertFalse(f.lower().endswith('.nev'))
        self.assertFalse(os.path.exists(self.remote_dir_root))
        os.makedirs(self.remote_dir_root)

        self.remote_data_dir = " ".join(file_util.gen_filenames(3))
        self.remote_data_dir_rawdata = " ".join(file_util.gen_filenames(3))
        self.assertNotEqual(self.remote_data_dir, self.remote_data_dir_rawdata)

        os.makedirs(os.path.join(self.remote_dir_root, self.remote_data_dir, 'leelab', 'cortex_exp_sorted'))

        self.site = {
            "path": "localhost",
            "prefix": joinpath_norm(self.remote_dir_root, self.remote_data_dir),
            "local": False
        }

        self.siteRaw = {
            "path": "localhost",
            "prefix": joinpath_norm(self.remote_dir_root, self.remote_data_dir_rawdata),
            "local": False
        }

        file_transfer_config = {
            "local_data_dir": "_data",
            "site_mapping_push": [
            ],
            "site_mapping_fetch": [
            ],
            "remote_site_config": {
                "localhost": {
                    "ssh_username": getpass.getuser(),
                    "ssh_port": 22
                }
            },
            "default_site": self.site,
            "quiet": True,
            "local_fetch_option": "copy"
        }
        with open("config/core/filetransfer/config.json", "wt") as f:
            json.dump(file_transfer_config, f)

        file_util.create_files_from_filelist(self.filelist_nev + self.filelist_nonev,
                                             local_data_dir=joinpath_norm(self.remote_dir_root,
                                                                          self.remote_data_dir_rawdata))
        self.system_info_file = os.path.join(self.__class__.local_save_dir, 'system_info')
        self.sacbatch_output_file = os.path.join(self.__class__.local_save_dir, 'sacbatch_output')

    def get_new_instance(self):
        with mock.patch(MockNames.git_repo_url, return_value=self.git_url), mock.patch(
                MockNames.git_repo_hash, return_value=self.git_hash), mock.patch(
            MockNames.git_check_clean, return_value=True):
            self.action = CortexExpSortedAction(
                CortexExpSortedAction.normalize_config({'spike_sorting_software_repo_path': self.git_repo_path,
                                                        'savepath': self.savepath}))
        self.assertEqual(self.action.config,
                         {'spike_sorting_software_repo_path': self.git_repo_path,
                          'spike_sorting_software_repo_hash': self.git_hash,
                          'spike_sorting_software_repo_url': self.git_url,
                          'savepath': self.savepath})

        self.assertFalse(os.path.exists(self.savepath))
        self.assertFalse(os.path.exists('query_template.py'))
        self.assertFalse(os.path.exists('prepare_result.p'))

        self.temp_dict['old_result'] = dict()
        self.temp_dict['old_result']['_id'] = ObjectId()
        self.temp_dict['old_result']['recorded_files'] = {}
        self.temp_dict['old_result']['recorded_files']['site'] = self.siteRaw
        self.filelist_this = random.sample(self.filelist_nev, 10) + random.sample(self.filelist_nonev, 10)
        random.shuffle(self.filelist_this)
        self.temp_dict['old_result']['recorded_files']['filelist'] = self.filelist_this

        # insert this doc in the DB.
        assert self.__class__.collection_client_raw.insert_one(self.temp_dict['old_result']).acknowledged

        self.temp_dict['correct_result'] = dict()
        self.temp_dict['correct_result']['schema_revision'] = 1
        self.temp_dict['correct_result']['cortex_exp_ref'] = self.temp_dict['old_result']['_id']
        self.temp_dict['correct_result']['files_to_sort'] = dict()
        self.temp_dict['correct_result']['files_to_sort']['site'] = self.siteRaw
        self.temp_dict['correct_result']['files_to_sort']['filelist'] = [f for f in self.filelist_this if
                                                                         f.lower().endswith('.nev')]
        # this field need updating later, to incorporate results inserted.
        self.temp_dict['correct_result']['sorted_files'] = dict()
        self.temp_dict['correct_result']['sorted_files']['site'] = deepcopy(self.site)
        self.temp_dict['correct_result']['sorted_files']['filelist'] = [os.path.basename(f) for f in self.filelist_this
                                                                        if f.lower().endswith('.nev')]

        self.temp_dict['correct_result']['sort_method'] = 'sacbatch_and_spikesort'
        self.temp_dict['correct_result']['sort_config'] = dict()

        # generate correct script.
        filelist_local = [os.path.basename(f) for f in self.temp_dict['correct_result']['files_to_sort']['filelist']]
        filelist_cell = ["'" + file + "'" for file in filelist_local]
        filelist_cell = "{" + ",".join(filelist_cell) + "}"
        sacbatch_script = util.load_config(self.action.__class__.config_path, 'sacbatch_script.m', load_json=False)
        spikesort_script = util.load_config(self.action.__class__.config_path, 'spikesort_script.m', load_json=False)
        sacbatch_script = sacbatch_script.format(filelist_cell)
        spikesort_script = spikesort_script.format(filelist_cell)
        main_script = util.load_config(self.action.__class__.config_path, 'sacbatch_and_spikesort_script.sh',
                                       load_json=False)

        self.temp_dict['correct_result']['sort_config']['system_info'] = " ".join(file_util.fake.sentences())
        self.temp_dict['correct_result']['sort_config']['sacbatch_output'] = " ".join(file_util.fake.sentences())
        self.temp_dict['correct_result']['sort_config']['action_config'] = deepcopy(self.action.config)
        self.temp_dict['correct_result']['sort_config']['sacbatch_file'] = 'SAC_batch_summer.tar.gz'
        self.temp_dict['correct_result']['sort_config']['spikesort_file'] = 'spikesort.tar.gz'
        self.temp_dict['correct_result']['sort_config']['sacbatch_script'] = sacbatch_script
        self.temp_dict['correct_result']['sort_config']['spikesort_script'] = spikesort_script
        self.temp_dict['correct_result']['sort_config']['master_script'] = main_script
        self.temp_dict['correct_result']['sort_person'] = 'Ge Huang'
        self.temp_dict['correct_result']['notes'] = " ".join(file_util.fake.sentences())

        self.temp_dict['timestamp_str'] = util.now_to_rfc3339_localoffset()
        # this is UTC.
        self.temp_dict['correct_result']['timestamp'] = util.rfc3339_to_datetime(self.temp_dict['timestamp_str'])

    def remove_instance(self):
        os.remove(self.savepath)
        os.remove('query_template.py')
        os.remove('prepare_result.p')

    def tearDown(self):
        self.assertFalse(os.path.exists(self.savepath))
        self.assertFalse(os.path.exists('query_template.py'))
        self.assertFalse(os.path.exists('prepare_result.p'))
        shutil.rmtree(self.git_repo_path)
        shutil.rmtree(self.remote_dir_root)
        # drop and then reset
        self.__class__.collection_client.drop()
        self.__class__.collection_client = self.__class__.db_client['leelab']['cortex_exp_sorted']
        #
        self.__class__.collection_client_raw.drop()
        self.__class__.collection_client_raw = self.__class__.db_client['temp']['temp']

    @classmethod
    def tearDownClass(cls):
        cls.collection_client.drop()
        cls.collection_client_raw.drop()
        cls.db_client.close()
        shutil.rmtree("config")

    def test_insert_correct_stuff(self):
        for _ in range(100):
            self.get_new_instance()
            self.temp_dict['wrong_type'] = 'correct'
            with mock.patch('builtins.input', side_effect=self.mock_function):
                self.assertFalse(self.action.is_prepared())
                self.action.run()
            self.assertTrue(self.action.is_finished())
            self.assertEqual(len(self.action.result_ids), 1)
            result_id = self.action.result_ids[0]
            result = self.__class__.collection_client.find_one({'_id': result_id})
            self.assertIsNotNone(result)
            del result['_id']

            # now time to augment correct result
            correct_result = self.temp_dict['correct_result']
            computed_append_prefix = os.path.join('leelab', 'cortex_exp_sorted', str(result_id))
            correct_result['sorted_files']['site']['append_prefix'] = computed_append_prefix
            correct_result['sorted_files']['filelist'] = [util.joinpath_norm(computed_append_prefix, f) for f in
                                                          correct_result['sorted_files']['filelist']]
            correct_result['sorted_files']['filelist'] = [f for i, f in
                                                          enumerate(correct_result['sorted_files']['filelist'])
                                                          if (i in self.temp_dict['keep_file_idx'])]
            self.assertEqual(correct_result, result)  # most important check.
            result['cortex_exp_ref'] = str(result['cortex_exp_ref'])
            result['timestamp'] = strict_rfc3339.timestamp_to_rfc3339_utcoffset(result['timestamp'].timestamp())
            self.assertTrue(schemautil.validate(CortexExpSortedSchemaJSL.get_schema(), result))
            self.action.revoke()
            result = self.__class__.collection_client.find_one({'_id': result_id})
            self.assertIsNone(result)
            # make sure the whole folder is also removed.
            self.assertFalse(os.path.exists(joinpath_norm(self.remote_dir_root, self.remote_data_dir,
                                                          'leelab', 'cortex_exp_sorted', str(result_id))))
            self.assertTrue(os.path.exists(joinpath_norm(self.remote_dir_root, self.remote_data_dir,
                                                         'leelab', 'cortex_exp_sorted')))

            self.remove_instance()

    @staticmethod
    def input_mock_function(prompt: str, instance) -> str:
        if prompt.startswith("Step 0"):
            # now it's time to pickle my result and let the template to load that stuff
            query_template_mock = """
from bson import ObjectId
query_doc = {{'_id': ObjectId('{}')}}
# make sure there's only one such doc, ignoring vulnerable window.
doc_count = client_instance['temp']['temp'].count(query_doc)
assert doc_count==1, "there must be only one matching doc!"
doc = client_instance['temp']['temp'].find_one(query_doc)
result = doc
            """.format(str(instance.temp_dict['old_result']['_id']))

            with open("query_template.py", "wt") as f:
                f.write(query_template_mock)
        elif prompt.startswith("Step 1"):
            with open(instance.action.config['savepath'], 'rt') as f_old:
                record_old = json.load(f_old)

            assert instance.temp_dict['old_result']['recorded_files'] == record_old['files_to_sort']
            record_old['files_to_sort']['filelist'] = [f for f in record_old['files_to_sort']['filelist'] if
                                                       f.lower().endswith('.nev')]
            record_old['sort_person'] = instance.temp_dict['correct_result']['sort_person']
            record_old['notes'] = instance.temp_dict['correct_result']['notes']
            record_old['timestamp'] = instance.temp_dict['timestamp_str']
            with open(instance.action.config['savepath'], 'wt') as f_new:
                json.dump(record_old, f_new)
        elif prompt.startswith("Step 2"):
            pass
        elif prompt.startswith("Step 3"):
            pass
        elif prompt.startswith("Step 4"):
            # create system_info,
            with open(instance.system_info_file, 'wt') as f:
                f.write(instance.temp_dict['correct_result']['sort_config']['system_info'])
            with open(instance.sacbatch_output_file, 'wt') as f:
                f.write(instance.temp_dict['correct_result']['sort_config']['sacbatch_output'])
        elif prompt.startswith("Step 5"):
            pass
        elif prompt.startswith("Step 6"):
            # remove some files.
            with open(instance.action.config['savepath'], 'rt') as f_old:
                record_old = json.load(f_old)
            assert len(record_old['sorted_files']['filelist']) == 10
            instance.temp_dict['keep_file_idx'] = random.sample(range(10), 5)  # keep 5 files.
            record_old['sorted_files']['filelist'] = [f for i, f in enumerate(record_old['sorted_files']['filelist'])
                                                      if (i in instance.temp_dict['keep_file_idx'])]
            with open(instance.action.config['savepath'], 'wt') as f_new:
                json.dump(record_old, f_new)
        elif prompt.startswith("please choose the method to do sorting"):
            return "1"
        elif prompt.startswith("press enter to start using method sacbatch_and_spikesort"):
            pass
        else:
            print(prompt)
            raise ValueError("impossible!")


if __name__ == '__main__':
    unittest.main(failfast=True)
