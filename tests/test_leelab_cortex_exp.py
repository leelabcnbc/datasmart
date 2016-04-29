import getpass
import hashlib
import json
import os
import random
import unittest
from functools import partial
from subprocess import CalledProcessError
import strict_rfc3339
from jsonschema.exceptions import ValidationError
from datasmart.actions.leelab.cortex_exp import CortexExpAction, CortexExpSchemaJSL, monkeylist
from datasmart.core import schemautil
from datasmart.core import util
from test_util import env_util, mock_util, file_util
import time


class LeelabCortexExpAction(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # check git is clean
        util.check_git_repo_clean()
        env_util.setup_db(cls, [CortexExpAction.table_path])



    def setUp(self):
        # check git is clean
        util.check_git_repo_clean()
        # I put setup here only to pass in reference to class for mock function.
        self.mock_function = partial(LeelabCortexExpAction.input_mock_function, instance=self)
        self.config_path = CortexExpAction.config_path



    def get_correct_result(self):
        # create the correct result.
        correct_result = dict()
        correct_result['schema_revision'] = 1
        correct_result['code_repo'] = dict()
        correct_result['code_repo']['repo_url'] = self.git_mock_info['git_url']
        correct_result['code_repo']['repo_hash'] = self.git_mock_info['git_hash']
        correct_result['monkey'] = random.choice(monkeylist)
        correct_result['experiment_name'] = self.temp_dict['experiment_name']
        correct_result['timing_file_name'] = self.temp_dict['timing_file_name']
        correct_result['condition_file_name'] = self.temp_dict['condition_file_name']
        correct_result['item_file_name'] = self.temp_dict['item_file_name']
        correct_result['recorded_files'] = dict()
        correct_result['recorded_files']['site'] = self.site
        correct_result['recorded_files']['filelist'] = self.filelist_true
        # TODO has some test case for this mapping stuff.
        correct_result['condition_stimulus_mapping'] = [
            {"condition_number": 1, "stimuli": ["a1.ctx", "a2.ctx"]},
            {"condition_number": 2, "stimuli": ["b1.ctx", "b2.ctx"]},
            {"condition_number": 3, "stimuli": ["a1.ctx", "b2.ctx"]},
            {"condition_number": 4, "stimuli": ["a2.ctx", "b1.ctx"]}
        ]
        correct_result['additional_parameters'] = " ".join(file_util.fake.sentences())
        correct_result['notes'] = " ".join(file_util.fake.sentences())

        correct_result['timing_file_sha1'] = self.temp_dict['timing_file_sha1']
        correct_result['condition_file_sha1'] = self.temp_dict['condition_file_sha1']
        correct_result['item_file_sha1'] = self.temp_dict['item_file_sha1']
        self.temp_dict['correct_result'] = correct_result

    def setup_cortex_exp_files(self):
        # creating item file, condition file, timing file, and their sha.
        self.temp_dict['experiment_name'] = "/".join(file_util.gen_filenames(random.randint(1, 2)))
        self.temp_dict['timing_file_name'] = file_util.gen_filename_strict_lower() + '.tm'
        self.temp_dict['condition_file_name'] = file_util.gen_filename_strict_lower() + '.cnd'
        self.temp_dict['item_file_name'] = file_util.gen_filename_strict_lower() + '.itm'
        filelist_full = [os.path.join(self.git_mock_info['git_repo_path'], self.temp_dict['experiment_name'], x) for x
                         in [self.temp_dict['timing_file_name'],
                             self.temp_dict['condition_file_name'],
                             self.temp_dict['item_file_name']]]
        file_util.create_files_from_filelist(filelist_full, local_data_dir='.')
        with open(filelist_full[0], 'rb') as f:
            self.temp_dict['timing_file_sha1'] = hashlib.sha1(f.read()).hexdigest()
        with open(filelist_full[1], 'rb') as f:
            self.temp_dict['condition_file_sha1'] = hashlib.sha1(f.read()).hexdigest()
        with open(filelist_full[2], 'rb') as f:
            self.temp_dict['item_file_sha1'] = hashlib.sha1(f.read()).hexdigest()
        file_util.create_files_from_filelist(self.filelist_true, local_data_dir=self.site['prefix'])

    def get_new_instance(self):
        # check git is clean
        util.check_git_repo_clean()


        filetransfer_config_text = """{{
            "local_data_dir": "_data",
            "site_mapping_push": [
            ],
            "site_mapping_fetch": [
            ],
            "remote_site_config": {{
              "localhost": {{
                "ssh_username": "{}",
                "ssh_port": 22
              }}
            }},
            "default_site": {{
              "path": "default_local_site",
              "local": true
            }},
            "quiet": false,
            "local_fetch_option": "copy"
          }}""".format(getpass.getuser())

        env_util.setup_local_config(('core', 'filetransfer'), filetransfer_config_text)

        self.dirs_to_cleanup = file_util.gen_unique_local_paths(1)  # for git
        file_util.create_dirs_from_dir_list(self.dirs_to_cleanup)
        self.git_mock_info = mock_util.setup_git_mock(git_repo_path=self.dirs_to_cleanup[0])
        self.savepath = file_util.gen_unique_local_paths(1)[0]
        self.temp_dict = {}
        self.site = env_util.setup_remote_site()
        filelist = file_util.gen_filelist(100, abs_path=False)
        self.filelist_true = filelist[:50]
        self.filelist_false = filelist[50:]
        self.action = mock_util.create_mocked_action(CortexExpAction,
                                                     {'cortex_expt_repo_path': self.git_mock_info['git_repo_path'],
                                                      'savepath': self.savepath},
                                                     {'git': self.git_mock_info})
        self.class_identifier = self.action.class_identifier
        self.files_to_cleanup = [self.savepath, 'query_template.py', 'prepare_result.p']

        for file in self.files_to_cleanup:
            self.assertFalse(os.path.exists(file))
        self.setup_cortex_exp_files()
        self.get_correct_result()

    def remove_instance(self):
        file_util.rm_files_from_file_list(self.files_to_cleanup)
        file_util.rm_dirs_from_dir_list(self.dirs_to_cleanup)
        env_util.teardown_remote_site(self.site)
        time.sleep(0.25)  # buffer time for removal
        for file in self.files_to_cleanup:
            self.assertFalse(os.path.exists(file))

        env_util.teardown_local_config()
        # check git is clean
        util.check_git_repo_clean()

    def tearDown(self):
        # drop and then reset
        env_util.reset_db(self.__class__, CortexExpAction.table_path)
        # check git is clean
        util.check_git_repo_clean()

    @classmethod
    def tearDownClass(cls):
        env_util.teardown_db(cls)
        # check git is clean
        util.check_git_repo_clean()




    def test_insert_wrong_stuff(self):
        wrong_types = ['missing field', 'wrong monkey',
                       'nonexistent tm', 'nonexistent itm', 'nonexistent cnd', 'nonexistent recording files']
        exception_types = [ValidationError, ValidationError,
                           AssertionError, AssertionError, AssertionError, CalledProcessError]
        exception_msgs = [None, None,
                          ".tm doesn't exist!", ".itm doesn't exist!", ".cnd doesn't exist!", None]

        for wrong_type, exception_type, exception_msg in zip(wrong_types, exception_types, exception_msgs):
            for _ in range(5):  # used to be 20. but somehow that will make program fail for travis
                self.get_new_instance()
                self.temp_dict['wrong_type'] = wrong_type
                with self.assertRaises(exception_type) as exp_instance:
                    mock_util.run_mocked_action(self.action, {'input': self.mock_function})
                if exception_msg is not None:
                    self.assertNotEqual(exp_instance.exception.args[0].find(exception_msg), -1)
                self.remove_instance()

    def test_insert_correct_stuff(self):
        for _ in range(20):  # used to be 100. but somehow that will make program fail for travis
            self.get_new_instance()
            self.temp_dict['wrong_type'] = 'correct'
            mock_util.run_mocked_action(self.action, {'input': self.mock_function})
            self.assertEqual(len(self.action.result_ids), 1)
            result_id = self.action.result_ids[0]
            result = env_util.assert_found_and_return(self.__class__, [result_id])[0]
            del result['_id']
            correct_result = self.temp_dict['correct_result']
            # for key in correct_result: # this for loop for of assert is easy to debug.
            #     self.assertEqual(correct_result[key], result[key])
            self.assertEqual(correct_result, result)
            result['timestamp'] = strict_rfc3339.timestamp_to_rfc3339_utcoffset(result['timestamp'].timestamp())
            del result['timing_file_sha1']
            del result['item_file_sha1']
            del result['condition_file_sha1']
            self.assertTrue(schemautil.validate(CortexExpSchemaJSL.get_schema(), result))
            self.action.revoke()
            env_util.assert_not_found(self.__class__, [result_id])
            self.remove_instance()

    @staticmethod
    def input_mock_function(prompt: str, instance) -> str:
        if prompt.startswith("{} Step 0a".format(instance.class_identifier)):
            pass
        elif prompt.startswith("{} Step 1".format(instance.class_identifier)):
            with open(instance.action.config['savepath'], 'rt') as f_old:
                record = json.load(f_old)

            # first, fill in the correct stuff.
            record['experiment_name'] = instance.temp_dict['correct_result']['experiment_name']
            record['timing_file_name'] = instance.temp_dict['correct_result']['timing_file_name']
            record['condition_file_name'] = instance.temp_dict['correct_result']['condition_file_name']
            record['item_file_name'] = instance.temp_dict['correct_result']['item_file_name']
            record['recorded_files'] = instance.temp_dict['correct_result']['recorded_files']
            record['additional_parameters'] = instance.temp_dict['correct_result']['additional_parameters']
            record['notes'] = instance.temp_dict['correct_result']['notes']
            record['monkey'] = instance.temp_dict['correct_result']['monkey']
            record['condition_stimulus_mapping'] = instance.temp_dict['correct_result']['condition_stimulus_mapping']
            # now time to compute the correct time.
            instance.temp_dict['correct_result']['timestamp'] = util.rfc3339_to_datetime(record['timestamp'])
            wrong_type = instance.temp_dict['wrong_type']
            if wrong_type == 'correct':
                pass
            elif wrong_type == 'missing field':
                # randomly remove one key
                del record[random.choice(list(record.keys()))]
            elif wrong_type == 'wrong monkey':
                record['monkey'] = random.choice(
                    ['Koko', 'Frugo', 'Leo', 'demo', 'koKo', 'lEo', 'gaBBy', None, 123123, 2.4])
            elif wrong_type == 'nonexistent tm':
                record['timing_file_name'] = file_util.gen_filename_strict_lower(
                    os.path.splitext(record['timing_file_name'])[0]) + '.tm'
            elif wrong_type == 'nonexistent cnd':
                record['condition_file_name'] = file_util.gen_filename_strict_lower(
                    os.path.splitext(record['condition_file_name'])[0]) + '.cnd'
            elif wrong_type == 'nonexistent itm':
                record['item_file_name'] = file_util.gen_filename_strict_lower(
                    os.path.splitext(record['item_file_name'])[0]) + '.itm'
            elif wrong_type == 'nonexistent recording files':
                record['recorded_files']['filelist'] = instance.filelist_false
            else:
                raise ValueError("impossible error type!")

            with open(instance.action.config['savepath'], 'wt') as f_new:
                json.dump(record, f_new)
        else:
            raise ValueError("impossible!")


if __name__ == '__main__':
    unittest.main()
