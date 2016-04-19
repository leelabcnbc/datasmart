import unittest
from datasmart.actions.leelab.cortex_exp_sorted import CortexExpSortedAction, CortexExpSortedSchemaJSL, sort_people
import os
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
import time

from test_util import mock_util, env_util, file_util


class LeelabCortexExpSortedAction(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # link to pymongo
        cls.collection_raw_key = ('temp', 'temp')
        env_util.setup_db(cls, [CortexExpSortedAction.table_path, cls.collection_raw_key])
        assert not os.path.exists("config")
        os.makedirs("config/core/filetransfer")
        cls.local_save_dir = '_data'  # this is the one used in the filetransfer config template.

    def setUp(self):
        self.mock_function = partial(LeelabCortexExpSortedAction.input_mock_function, instance=self)

    def generate_files_for_sacbatch_and_spikesort(self):
        # create files for sort
        with open(os.path.join(self.git_mock_info['git_repo_path'], 'SAC_batch_summer.tar.gz'), 'wt') as f:
            f.close()
        with open(os.path.join(self.git_mock_info['git_repo_path'], 'spikesort.tar.gz'), 'wt') as f:
            f.close()

    def get_new_instance(self):
        self.dirs_to_cleanup = file_util.gen_unique_local_paths(1)  # 1 for git
        file_util.create_dirs_from_dir_list(self.dirs_to_cleanup)
        self.git_mock_info = mock_util.setup_git_mock(git_repo_path=self.dirs_to_cleanup[0])
        self.savepath = file_util.gen_unique_local_paths(1)[0]
        self.temp_dict = {}
        self.site = env_util.setup_remote_site(['leelab', 'cortex_exp_sorted'])
        self.site_raw = env_util.setup_remote_site()
        self.action = mock_util.create_mocked_action(CortexExpSortedAction,
                                                     {'spike_sorting_software_repo_path': self.git_mock_info[
                                                         'git_repo_path'],
                                                      'savepath': self.savepath},
                                                     {'git': self.git_mock_info})

        # generate files to fetch for SAC batch.
        self.generate_files_for_sacbatch_and_spikesort()

        filelist = file_util.gen_filelist(100, abs_path=False)
        self.filelist_nev = [f + '.nev' for f in filelist[:50]]
        self.filelist_nonev = filelist[50:]
        for f in self.filelist_nonev:
            # make sure false files don't end with nev. this should be correct, since that fake library doesn't produce
            # .nev names.
            self.assertFalse(f.lower().endswith('.nev'))

        file_transfer_config = {
            "local_data_dir": self.__class__.local_save_dir,
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
        # write the particular site config.
        with open("config/core/filetransfer/config.json", "wt") as f:
            json.dump(file_transfer_config, f)

        file_util.create_files_from_filelist(self.filelist_nev + self.filelist_nonev,
                                             local_data_dir=self.site_raw['prefix'])
        self.system_info_file = os.path.join(self.__class__.local_save_dir, 'system_info')
        self.sacbatch_output_file = os.path.join(self.__class__.local_save_dir, 'sacbatch_output')

        self.class_identifier = self.action.class_identifier
        self.files_to_cleanup = [self.savepath, 'query_template.py', 'prepare_result.p',
                                 self.system_info_file, self.sacbatch_output_file] + \
                                [os.path.join(self.__class__.local_save_dir, os.path.basename(x)) for x in
                                 self.filelist_nev]

        self.files_to_cleanup_sacbatch_and_spikesort = [os.path.join(self.__class__.local_save_dir, x) for x in
                                                        ['sacbatch_and_spikesort_script.sh',
                                                         'SAC_batch.tar.gz', 'spikesort.tar.gz',
                                                         'sacbatch_script.m', 'spikesort_script.m']]

        for file in self.files_to_cleanup + self.files_to_cleanup_sacbatch_and_spikesort:
            self.assertFalse(os.path.exists(file))

        self.temp_dict['old_result'] = dict()
        self.temp_dict['old_result']['_id'] = ObjectId()
        self.temp_dict['old_result']['recorded_files'] = {}
        self.temp_dict['old_result']['recorded_files']['site'] = self.site_raw
        self.filelist_this = self.filelist_nev + self.filelist_nonev
        random.shuffle(self.filelist_this)
        self.temp_dict['old_result']['recorded_files']['filelist'] = self.filelist_this

        # insert this doc in the DB.
        assert self.__class__.collection_clients[self.__class__.collection_raw_key].insert_one(
            self.temp_dict['old_result']).acknowledged

        self.temp_dict['correct_result'] = dict()
        self.temp_dict['correct_result']['schema_revision'] = 1
        self.temp_dict['correct_result']['cortex_exp_ref'] = self.temp_dict['old_result']['_id']
        self.temp_dict['correct_result']['files_to_sort'] = dict()
        self.temp_dict['correct_result']['files_to_sort']['site'] = self.site_raw
        self.temp_dict['correct_result']['files_to_sort']['filelist'] = [f for f in self.filelist_this if
                                                                         f.lower().endswith('.nev')]
        # this field need updating later, to incorporate results inserted.
        self.temp_dict['correct_result']['sorted_files'] = dict()
        self.temp_dict['correct_result']['sorted_files']['site'] = deepcopy(
            self.site)  # don't interfere with my original site.
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
        self.temp_dict['correct_result']['sort_person'] = random.choice(sort_people)
        self.temp_dict['correct_result']['notes'] = " ".join(file_util.fake.sentences())

    def remove_instance(self):
        file_util.rm_files_from_file_list(self.files_to_cleanup, must_exist=False)
        file_util.rm_files_from_file_list(self.files_to_cleanup_sacbatch_and_spikesort)
        time.sleep(0.1)   # buffer time for removal
        for file in self.files_to_cleanup + self.files_to_cleanup_sacbatch_and_spikesort:
            self.assertFalse(os.path.exists(file))
        file_util.rm_dirs_from_dir_list(self.dirs_to_cleanup)
        env_util.teardown_remote_site(self.site)
        env_util.teardown_remote_site(self.site_raw)
        time.sleep(0.1)   # buffer time for removal

    def tearDown(self):
        # drop and then reset
        env_util.reset_db(self.__class__, [CortexExpSortedAction.table_path, self.__class__.collection_raw_key])

    @classmethod
    def tearDownClass(cls):
        env_util.teardown_db(cls)
        env_util.teardown_local_config()

    def test_insert_correct_stuff(self):
        for _ in range(100):
            self.get_new_instance()
            self.temp_dict['wrong_type'] = 'correct'
            mock_util.run_mocked_action(self.action, {'input': self.mock_function})
            self.assertEqual(len(self.action.result_ids), 1)
            result_id = self.action.result_ids[0]
            result = env_util.assert_found_and_return(self.__class__, [result_id],
                                                      client_key=CortexExpSortedAction.table_path)[0]
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
            for key in correct_result:  # this for loop for of assert is easy to debug.
                self.assertEqual(correct_result[key], result[key])
            self.assertEqual(correct_result, result)  # most important check.
            # make sure files are indeed uploaded.
            files_uploaded = os.listdir(os.path.join(result['sorted_files']['site']['prefix'], computed_append_prefix))
            files_uploaded = [x for x in files_uploaded if not x.startswith('.')]
            files_uploaded_record = [os.path.basename(x) for x in result['sorted_files']['filelist']]
            self.assertEqual(sorted(files_uploaded), sorted(files_uploaded_record))
            result['cortex_exp_ref'] = str(result['cortex_exp_ref'])
            result['timestamp'] = strict_rfc3339.timestamp_to_rfc3339_utcoffset(result['timestamp'].timestamp())
            self.assertTrue(schemautil.validate(CortexExpSortedSchemaJSL.get_schema(), result))
            self.action.revoke()
            env_util.assert_not_found(self.__class__, [result_id], client_key=CortexExpSortedAction.table_path)
            # make sure the whole folder is also removed.
            self.assertFalse(os.path.exists(joinpath_norm(self.site['prefix'], 'leelab',
                                                          'cortex_exp_sorted', str(result_id))))
            self.assertTrue(os.path.exists(joinpath_norm(self.site['prefix'], 'leelab', 'cortex_exp_sorted')))

            self.remove_instance()

    @staticmethod
    def input_mock_function(prompt: str, instance) -> str:
        if prompt.startswith("{} Step 0a".format(instance.class_identifier)):
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
        elif prompt.startswith("{} Step 2.1".format(instance.class_identifier)):
            with open(instance.action.config['savepath'], 'rt') as f_old:
                record_old = json.load(f_old)

            assert instance.temp_dict['old_result']['recorded_files'] == record_old['files_to_sort']
            record_old['files_to_sort']['filelist'] = [f for f in record_old['files_to_sort']['filelist'] if
                                                       f.lower().endswith('.nev')]
            record_old['sort_person'] = instance.temp_dict['correct_result']['sort_person']
            record_old['notes'] = instance.temp_dict['correct_result']['notes']
            instance.temp_dict['correct_result']['timestamp'] = util.rfc3339_to_datetime(record_old['timestamp'])

            with open(instance.action.config['savepath'], 'wt') as f_new:
                json.dump(record_old, f_new)
        elif prompt.startswith("{} Step 2.2".format(instance.class_identifier)):
            pass
        elif prompt.startswith("{} Step 2.3".format(instance.class_identifier)):
            pass
        elif prompt.startswith("{} Step 2.4".format(instance.class_identifier)):
            # create system_info,
            with open(instance.system_info_file, 'wt') as f:
                f.write(instance.temp_dict['correct_result']['sort_config']['system_info'])
            with open(instance.sacbatch_output_file, 'wt') as f:
                f.write(instance.temp_dict['correct_result']['sort_config']['sacbatch_output'])
        elif prompt.startswith("{} Step 2.5".format(instance.class_identifier)):
            pass
        elif prompt.startswith("{} Step 2.6".format(instance.class_identifier)):
            # remove some files.
            with open(instance.action.config['savepath'], 'rt') as f_old:
                record_old = json.load(f_old)
            assert len(record_old['sorted_files']['filelist']) == 50
            # keep 5 files.
            instance.temp_dict['keep_file_idx'] = random.sample(range(len(record_old['sorted_files']['filelist'])), 5)
            record_old['sorted_files']['filelist'] = [f for i, f in enumerate(record_old['sorted_files']['filelist'])
                                                      if (i in instance.temp_dict['keep_file_idx'])]
            with open(instance.action.config['savepath'], 'wt') as f_new:
                json.dump(record_old, f_new)
        elif prompt.startswith("{} Step 1a".format(instance.class_identifier)):
            return "1"
        elif prompt.startswith("{} Step 1b press enter to start using method sacbatch_and_spikesort".format(
                instance.class_identifier)):
            pass
        else:
            print(prompt)
            raise ValueError("impossible!")


if __name__ == '__main__':
    unittest.main(failfast=True)
