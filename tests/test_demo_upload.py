import unittest
from datasmart.actions.demo.file_upload import FileUploadAction


class MyTestCase(unittest.TestCase):
    def test_something(self):
        a = FileUploadAction()
        self.assertEqual(True, True)


if __name__ == '__main__':
    unittest.main()
