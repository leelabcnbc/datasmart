import unittest
import unittest.mock as mock
import test_util
from test_util import MockNames
import os
import shutil
from datasmart.actions.leelab.cortex_exp import CortexExpAction
import pymongo
from bson import ObjectId
import json
from functools import partial
from jsonschema.exceptions import ValidationError
import random

class LeelabCortexExpAction(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # link to pymongo
        cls.db_client = pymongo.MongoClient()
        cls.collection_client = cls.db_client['leelab']['cortex_exp']

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

    def tearDown(self):
        self.assertFalse(os.path.exists(self.savepath))
        self.assertFalse(os.path.exists('query_template.py'))
        self.assertFalse(os.path.exists('prepare_result.p'))
        shutil.rmtree(self.git_repo_path)
        # drop and then reset
        self.__class__.collection_client.drop()
        self.__class__.collection_client = self.__class__.db_client['leelab']['cortex_exp']

    @classmethod
    def tearDownClass(cls):
        cls.collection_client.drop()
        cls.db_client.close()

    def test_insert_wrong_stuff(self):
        wrong_types = ['missing field', 'wrong monkey',
                       'nonexistent recording files', 'nonexistent tm',
                       'nonexistent itm', 'nonexistent cnd']
        wrong_types = ['missing field', 'wrong monkey']
        for wrong_type in wrong_types:
            self.temp_dict['wrong_type'] = wrong_type
            for _ in range(10):
                self.assertFalse(os.path.exists(self.savepath))
                self.assertFalse(os.path.exists('query_template.py'))
                self.assertFalse(os.path.exists('prepare_result.p'))
                self.get_new_instance()
                with mock.patch('builtins.input', side_effect=self.mock_function),\
                        mock.patch('builtins.print'):
                    with self.assertRaises(ValidationError):
                        self.assertFalse(self.action.is_prepared())
                        self.action.run()
                self.assertTrue(os.path.exists(self.savepath))
                self.assertTrue(os.path.exists('query_template.py'))
                self.assertTrue(os.path.exists('prepare_result.p'))
                os.remove(self.savepath)
                os.remove('query_template.py')
                os.remove('prepare_result.p')

    def test_insert_correct_stuff(self):
        for _ in range(100):
            pass


    @staticmethod
    def input_mock_function(prompt: str, instance) -> str:
        if prompt.startswith("Step 0"):
            pass
        elif prompt.startswith("Step 1"):
            with open(instance.action.config['savepath'], 'rt') as f_old:
                record = json.load(f_old)
            wrong_type = instance.temp_dict['wrong_type']
            if wrong_type == 'missing field':
                # randomly remove one key
                del record[random.choice(list(record.keys()))]
            elif wrong_type == 'wrong monkey':
                record['monkey'] = random.choice(['Koko','Frugo','Leo','demo','koKo','lEo', 'gaBBy', None, 123123, 2.4])
            else:
                raise ValueError("impossible error type!")

            with open(instance.action.config['savepath'], 'wt') as f_new:
                json.dump(record, f_new)
        else:
            raise ValueError("impossible!")




if __name__ == '__main__':
    unittest.main()
