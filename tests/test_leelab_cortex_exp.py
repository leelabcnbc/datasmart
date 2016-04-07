import unittest
import unittest.mock as mock
import test_util
from test_util import MockNames
import os
import shutil
from datasmart.actions.leelab.cortex_exp import CortexExpAction
import pymongo
from bson import ObjectId


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

        # create git_repo_path.
        os.makedirs(self.git_repo_path)
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
                       'nonexistent recording files', 'nonexistent ',
                       'nonexistent itm', 'nonexistent cnd']
        for wrong_type in wrong_types:
            pass

    def test_insert_correct_stuff(self):
        for _ in range(100):
            pass


    def input_mock_function(self):
        pass


if __name__ == '__main__':
    unittest.main()
