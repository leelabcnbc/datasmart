import unittest
from datasmart.actions.demo.file_download import FileDownloadAction


class MyTestCase(unittest.TestCase):
    def test_something(self):
        a = FileDownloadAction()
        self.assertEqual(True, True)


if __name__ == '__main__':
    unittest.main()
