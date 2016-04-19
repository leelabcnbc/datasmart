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
from datasmart.actions.leelab.cortex_exp import CortexExpAction, CortexExpSchemaJSL
from datasmart.core import schemautil
from datasmart.core import util
from test_util import env_util, mock_util, file_util


class LeelabCortexExpAction(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        env_util.setup_db(cls, ('leelab', 'cortex_exp'))
        with open("filetransfer_local_config.json.template", "rt") as f:
            filetransfer_config_text = f.read().format(getpass.getuser())
        env_util.setup_local_config(('core', 'filetransfer'), filetransfer_config_text)

    def setUp(self):
        self.mock_function = partial(LeelabCortexExpAction.input_mock_function, instance=self)

    def get_new_instance(self):
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
        self.files_to_cleanup = [self.savepath, 'query_template.py', 'prepare_result.p']

        for file in self.files_to_cleanup:
            self.assertFalse(os.path.exists(file))

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

    def remove_instance(self):
        file_util.rm_files_from_file_list(self.files_to_cleanup)
        file_util.rm_dirs_from_dir_list(self.dirs_to_cleanup)
        env_util.teardown_remote_site(self.site)

        for file in self.files_to_cleanup:
            self.assertFalse(os.path.exists(file))

    def tearDown(self):
        # drop and then reset
        self.__class__.collection_client.drop()
        self.__class__.collection_client = self.__class__.db_client['leelab']['cortex_exp']

    @classmethod
    def tearDownClass(cls):
        env_util.teardown_db(cls)
        env_util.teardown_local_config()

    def test_insert_wrong_stuff(self):
        wrong_types = ['missing field', 'wrong monkey',
                       'nonexistent tm', 'nonexistent itm', 'nonexistent cnd', 'nonexistent recording files']
        exception_types = [ValidationError, ValidationError,
                           AssertionError, AssertionError, AssertionError, CalledProcessError]
        exception_msgs = [None, None,
                          ".tm doesn't exist!", ".itm doesn't exist!", ".cnd doesn't exist!", None]

        for wrong_type, exception_type, exception_msg in zip(wrong_types, exception_types, exception_msgs):
            for _ in range(20):
                self.get_new_instance()
                self.temp_dict['wrong_type'] = wrong_type
                with self.assertRaises(exception_type) as exp_instance:
                    mock_util.run_mocked_action(self.action, {'input': self.mock_function})
                if exception_msg is not None:
                    self.assertNotEqual(exp_instance.exception.args[0].find(exception_msg), -1)
                self.remove_instance()

    def test_insert_correct_stuff(self):
        for _ in range(100):
            self.get_new_instance()
            self.temp_dict['wrong_type'] = 'correct'
            mock_util.run_mocked_action(self.action, {'input': self.mock_function})
            self.assertTrue(self.action.is_finished())
            self.assertEqual(len(self.action.result_ids), 1)
            result_id = self.action.result_ids[0]
            result = self.__class__.collection_client.find_one({'_id': result_id})
            self.assertIsNotNone(result)
            self.assertEqual(result['timing_file_sha1'], self.temp_dict['timing_file_sha1'])
            self.assertEqual(result['condition_file_sha1'], self.temp_dict['condition_file_sha1'])
            self.assertEqual(result['item_file_sha1'], self.temp_dict['item_file_sha1'])
            self.assertTrue(self.action.is_finished())
            del result['timing_file_sha1']
            del result['condition_file_sha1']
            del result['item_file_sha1']
            del result['_id']
            timestamp1 = result['timestamp'].timestamp()
            result['timestamp'] = strict_rfc3339.timestamp_to_rfc3339_utcoffset(timestamp1)
            self.assertTrue(schemautil.validate(CortexExpSchemaJSL.get_schema(), result))
            timestamp2 = util.rfc3339_to_timestamp(result['timestamp'])
            self.assertLessEqual(abs(timestamp1 - timestamp2), 1.0)  # less than 1s in deviation. (pretty loose bound)
            self.action.revoke()
            result = self.__class__.collection_client.find_one({'_id': result_id})
            self.assertIsNone(result)
            self.remove_instance()

    @staticmethod
    def input_mock_function(prompt: str, instance) -> str:
        if prompt.startswith("Step 0"):
            pass
        elif prompt.startswith("Step 1"):
            with open(instance.action.config['savepath'], 'rt') as f_old:
                record = json.load(f_old)

            # first, fill in the correct stuff.
            record['experiment_name'] = instance.temp_dict['experiment_name']
            record['timing_file_name'] = instance.temp_dict['timing_file_name']
            record['condition_file_name'] = instance.temp_dict['condition_file_name']
            record['item_file_name'] = instance.temp_dict['item_file_name']
            record['recorded_files']['site'] = instance.site
            record['recorded_files']['filelist'] = instance.filelist_true

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
                record['timing_file_name'] = 'a' + record['timing_file_name']
            elif wrong_type == 'nonexistent cnd':
                record['condition_file_name'] = 'a' + record['condition_file_name']
            elif wrong_type == 'nonexistent itm':
                record['item_file_name'] = 'a' + record['item_file_name']
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
