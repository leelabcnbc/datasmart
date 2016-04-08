import unittest
import unittest.mock as mock
import test_util
from test_util import MockNames
import os
import shutil
from datasmart.actions.leelab.cortex_exp import CortexExpAction, CortexExpSchemaJSL
import pymongo
import json
from functools import partial
from jsonschema.exceptions import ValidationError
import random
from subprocess import CalledProcessError
import hashlib
from datasmart.core.util import joinpath_norm
import getpass
from datasmart.core import schemautil
from datasmart.core import util
import strict_rfc3339


class LeelabCortexExpAction(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # link to pymongo
        cls.db_client = pymongo.MongoClient()
        cls.collection_client = cls.db_client['leelab']['cortex_exp']
        assert not os.path.exists("config")
        with open("filetransfer_local_config.json.template", "rt") as f:
            filetransfer_config_text = f.read().format(getpass.getuser())
        os.makedirs("config/core/filetransfer")
        with open("config/core/filetransfer/config.json", "wt") as f:
            f.write(filetransfer_config_text)

    def setUp(self):
        self.git_url = 'http://git.example.com'
        self.git_hash = '0000000000000000000000000000000000000000'
        self.git_repo_path = " ".join(test_util.gen_filenames(3))
        self.savepath = " ".join(test_util.gen_filenames(3))
        self.assertNotEqual(self.git_repo_path, self.savepath)  # should be (almost) always true
        self.temp_dict = {}
        self.mock_function = partial(LeelabCortexExpAction.input_mock_function, instance=self)

        # create git_repo_path.
        os.makedirs(self.git_repo_path)

        self.assertFalse(os.path.exists(self.savepath))
        self.assertFalse(os.path.exists('query_template.py'))
        self.assertFalse(os.path.exists('prepare_result.p'))

        #
        self.remote_dir_root = os.path.abspath(" ".join(test_util.gen_filenames(3)))
        filelist = test_util.gen_filelist(100, abs_path=False)
        self.filelist_true = filelist[:50]
        self.filelist_false = filelist[50:]
        self.assertFalse(os.path.exists(self.remote_dir_root))
        os.makedirs(self.remote_dir_root)
        self.remote_data_dir = " ".join(test_util.gen_filenames(3))

        self.site = {
            "path": "localhost",
            "prefix": joinpath_norm(self.remote_dir_root, self.remote_data_dir),
            "local": False
        }

    def get_new_instance(self):
        with mock.patch(MockNames.git_repo_url, return_value=self.git_url), mock.patch(
                MockNames.git_repo_hash, return_value=self.git_hash), mock.patch(
            MockNames.git_check_clean, return_value=True):
            self.action = CortexExpAction(CortexExpAction.normalize_config({'cortex_expt_repo_path': self.git_repo_path,
                                                                            'savepath': self.savepath}))
        self.assertEqual(self.action.config,
                         {'cortex_expt_repo_path': self.git_repo_path,
                          'cortex_expt_repo_hash': self.git_hash,
                          'cortex_expt_repo_url': self.git_url, 'savepath': self.savepath})

        self.assertFalse(os.path.exists(self.savepath))
        self.assertFalse(os.path.exists('query_template.py'))
        self.assertFalse(os.path.exists('prepare_result.p'))

        self.temp_dict['experiment_name'] = "/".join(test_util.gen_filenames(random.randint(1, 2)))
        self.temp_dict['timing_file_name'] = test_util.gen_filename_strict_lower() + '.tm'
        self.temp_dict['condition_file_name'] = test_util.gen_filename_strict_lower() + '.cnd'
        self.temp_dict['item_file_name'] = test_util.gen_filename_strict_lower() + '.itm'
        filelist_full = [os.path.join(self.git_repo_path, self.temp_dict['experiment_name'],
                                      x) for x in [self.temp_dict['timing_file_name'],
                                                   self.temp_dict['condition_file_name'],
                                                   self.temp_dict['item_file_name']]]
        test_util.create_files_from_filelist(filelist_full, local_data_dir='.')

        with open(filelist_full[0], 'rb') as f:
            self.temp_dict['timing_file_sha1'] = hashlib.sha1(f.read()).hexdigest()
        with open(filelist_full[1], 'rb') as f:
            self.temp_dict['condition_file_sha1'] = hashlib.sha1(f.read()).hexdigest()
        with open(filelist_full[2], 'rb') as f:
            self.temp_dict['item_file_sha1'] = hashlib.sha1(f.read()).hexdigest()
        test_util.create_files_from_filelist(self.filelist_true, local_data_dir=self.site['prefix'])

    def remove_instance(self):
        os.remove(self.savepath)
        os.remove('query_template.py')
        os.remove('prepare_result.p')
        shutil.rmtree(os.path.join(self.git_repo_path, self.temp_dict['experiment_name']))
        shutil.rmtree(self.site['prefix'])

    def tearDown(self):
        self.assertFalse(os.path.exists(self.savepath))
        self.assertFalse(os.path.exists('query_template.py'))
        self.assertFalse(os.path.exists('prepare_result.p'))
        shutil.rmtree(self.git_repo_path)
        shutil.rmtree(self.remote_dir_root)
        # drop and then reset
        self.__class__.collection_client.drop()
        self.__class__.collection_client = self.__class__.db_client['leelab']['cortex_exp']

    @classmethod
    def tearDownClass(cls):
        cls.collection_client.drop()
        cls.db_client.close()
        shutil.rmtree("config")

    def test_insert_wrong_stuff(self):
        wrong_types = ['missing field', 'wrong monkey',
                       'nonexistent tm', 'nonexistent itm', 'nonexistent cnd', 'nonexistent recording files']
        exception_types = [ValidationError, ValidationError,
                           AssertionError, AssertionError, AssertionError, CalledProcessError]
        exception_msgs = [None, None,
                          ".tm doesn't exist!", ".itm doesn't exist!", ".cnd doesn't exist!", None]

        for wrong_type, exception_type, exception_msg in zip(wrong_types, exception_types, exception_msgs):
            self.temp_dict['wrong_type'] = wrong_type
            for _ in range(20):
                self.get_new_instance()
                with mock.patch('builtins.input', side_effect=self.mock_function):
                    with self.assertRaises(exception_type) as exp_instance:
                        self.assertFalse(self.action.is_prepared())
                        self.action.run()
                if exception_msg is not None:
                    self.assertNotEqual(exp_instance.exception.args[0].find(exception_msg), -1)
                self.remove_instance()

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
