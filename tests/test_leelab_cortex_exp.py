import unittest
from datasmart.actions.leelab.cortex_exp import CortexExpAction


class MyTestCase(unittest.TestCase):
    def test_something(self):
        a = CortexExpAction({'cortex_expt_repo_url': '1',
                'cortex_expt_repo_hash': '1',
                'cortex_expt_repo_path': '1'})
        self.assertEqual(True, True)


if __name__ == '__main__':
    unittest.main()
