import json
import os
import random

import unittest
from functools import partial
from faker import Factory

from jsonschema.exceptions import ValidationError
from datasmart.core.util.datetime import (datetime_local_to_rfc3339_local,
                                          datetime_to_datetime_utc, rfc3339_to_datetime)
import datasmart.core.util.git
from datasmart.actions.demo.school_grade_input import (SchoolGradeInputAction,
                                                       subjectlist, SchoolGradeJSL)
from datasmart.core import schemautil
from datasmart.test_util import env_util
from datasmart.test_util import mock_util, file_util
from datasmart.core.util.io import load_file, save_file
from copy import deepcopy

# make sure repetable.
random.seed(0)
fake = Factory.create()
fake.seed(0)


def get_correct_result_single(get_timestamp=False):
    # create the correct result.
    correct_result = dict()
    correct_result['first_name'] = fake.first_name()
    correct_result['last_name'] = fake.last_name()
    correct_result['subject'] = random.choice(subjectlist)
    correct_result['score'] = random.randint(0, 100)
    if get_timestamp:
        correct_result['timestamp'] = datetime_local_to_rfc3339_local(datetime_to_datetime_utc(fake.date_time()))
        if random.random() > 0.5:
            correct_result['notes'] = fake.sentence()
    return correct_result


class DemoSchoolGradeInputAction(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # check git is clean
        datasmart.core.util.git.check_git_repo_clean()
        env_util.setup_db(cls, [SchoolGradeInputAction.table_path])

    def setUp(self):
        # check git is clean
        datasmart.core.util.git.check_git_repo_clean()
        # I put setup here only to pass in reference to class for mock function.
        self.config_path = SchoolGradeInputAction.config_path
        self.mock_function = partial(DemoSchoolGradeInputAction.input_mock_function, instance=self)

    def get_correct_result(self, batch=False, num=1):
        if not batch:
            self.temp_dict['correct_result'] = get_correct_result_single()
        else:
            self.temp_dict['correct_results'] = []
            for _ in range(num):
                self.temp_dict['correct_results'].append(get_correct_result_single(get_timestamp=True))

    def get_new_instance_batch(self, num_record_to_use):
        self.temp_dict = {}
        # in batch mode, we even don't need any
        datasmart.core.util.git.check_git_repo_clean()
        self.get_correct_result(batch=True, num=num_record_to_use)
        self.action = mock_util.create_mocked_action(SchoolGradeInputAction,
                                                     {'batch_records': deepcopy(self.temp_dict['correct_results'])})
        self.class_identifier = self.action.class_identifier
        self.files_to_cleanup = [self.action.prepare_result_name, self.action.query_template_name]

        for file in self.files_to_cleanup:
            self.assertFalse(os.path.exists(file))

    def get_new_instance_single(self):
        datasmart.core.util.git.check_git_repo_clean()
        self.temp_dict = {}
        self.savepath = file_util.gen_unique_local_paths(1)[0]
        self.action = mock_util.create_mocked_action(SchoolGradeInputAction, {'savepath': self.savepath})
        self.class_identifier = self.action.class_identifier
        self.files_to_cleanup = [self.savepath, self.action.prepare_result_name, self.action.query_template_name]

        for file in self.files_to_cleanup:
            self.assertFalse(os.path.exists(file))

        self.get_correct_result()

    def remove_instance(self):
        file_util.rm_files_from_file_list(self.files_to_cleanup)
        for file in self.files_to_cleanup:
            self.assertFalse(os.path.exists(file))
        # check git is clean
        datasmart.core.util.git.check_git_repo_clean()

    def tearDown(self):
        # drop and then reset
        env_util.reset_db(self.__class__, SchoolGradeInputAction.table_path)
        # check git is clean
        datasmart.core.util.git.check_git_repo_clean()

    @classmethod
    def tearDownClass(cls):
        env_util.teardown_db(cls)
        # check git is clean
        datasmart.core.util.git.check_git_repo_clean()

    def test_insert_wrong_stuff(self):
        wrong_types = ['missing field', 'wrong subject', 'invalid score']
        exception_types = [ValidationError, ValidationError, ValidationError]
        exception_msgs = [None, None, None]

        for wrong_type, exception_type, exception_msg in zip(wrong_types, exception_types, exception_msgs):
            for _ in range(5):  # used to be 20. but somehow that will make program fail for travis
                self.get_new_instance_single()
                self.temp_dict['wrong_type'] = wrong_type
                with self.assertRaises(exception_type) as exp_instance:
                    mock_util.run_mocked_action(self.action, {'input': self.mock_function})
                if exception_msg is not None:
                    self.assertNotEqual(exp_instance.exception.args[0].find(exception_msg), -1)
                self.remove_instance()

    def test_insert_correct_stuff_single(self):
        for _ in range(20):  # used to be 100. but somehow that will make program fail for travis
            self.get_new_instance_single()
            self.temp_dict['wrong_type'] = 'correct'
            mock_util.run_mocked_action(self.action, {'input': self.mock_function})
            self.assertEqual(len(self.action.result_ids), 1)
            result_id = self.action.result_ids[0]
            result = env_util.assert_found_and_return(self.__class__, [result_id])[0]
            del result['_id']
            correct_result = self.temp_dict['correct_result']
            self.assertEqual(correct_result, result)
            result['timestamp'] = datetime_to_datetime_utc(result['timestamp'])
            result['timestamp'] = datetime_local_to_rfc3339_local(result['timestamp'])
            self.assertTrue(schemautil.validate(SchoolGradeJSL.get_schema(), result))
            self.action.revoke()
            env_util.assert_not_found(self.__class__, [result_id])
            self.remove_instance()

    def test_insert_correct_stuff_batch(self):
        counter_dict = {}
        num_record_list = [1, 5, 100]
        for _ in range(20):  # used to be 100. but somehow that will make program fail for travis
            num_record_to_use = random.choice(num_record_list)
            counter_dict[num_record_to_use] = True
            self.get_new_instance_batch(num_record_to_use)  # insert
            self.temp_dict['wrong_type'] = 'correct'
            mock_util.run_mocked_action(self.action)
            self.assertEqual(len(self.action.result_ids), num_record_to_use)
            results = env_util.assert_found_and_return(self.__class__, self.action.result_ids)
            correct_results = self.temp_dict['correct_results']
            self.assertEqual(len(results), len(correct_results))
            for x, y in zip(results, correct_results):
                del x['_id']
                y['timestamp'] = rfc3339_to_datetime(y['timestamp'])
                self.assertEqual(x, y)
                x['timestamp'] = datetime_to_datetime_utc(x['timestamp'])
                x['timestamp'] = datetime_local_to_rfc3339_local(x['timestamp'])
                self.assertTrue(schemautil.validate(SchoolGradeJSL.get_schema(), x))
            self.action.revoke()
            env_util.assert_not_found(self.__class__, self.action.result_ids)
            self.remove_instance()
        assert len(counter_dict) == len(num_record_list)

    @staticmethod
    def input_mock_function(prompt: str, instance) -> str:
        if prompt.startswith("{} Step 0a".format(instance.class_identifier)):
            pass
        elif prompt.startswith("{} Step 1".format(instance.class_identifier)):
            record = load_file(instance.action.config['savepath'], load_json=True)

            # first, fill in the correct stuff.
            record['first_name'] = instance.temp_dict['correct_result']['first_name']
            record['last_name'] = instance.temp_dict['correct_result']['last_name']
            record['subject'] = instance.temp_dict['correct_result']['subject']
            record['score'] = instance.temp_dict['correct_result']['score']
            if 'notes' in instance.temp_dict['correct_result']:
                record['notes'] = instance.temp_dict['correct_result']['notes']
            else:
                del record['notes']
            instance.temp_dict['correct_result']['timestamp'] = rfc3339_to_datetime(record['timestamp'])
            wrong_type = instance.temp_dict['wrong_type']
            if wrong_type == 'correct':
                pass
            elif wrong_type == 'missing field':
                # randomly remove one key
                del record[random.choice(['first_name', 'last_name', 'subject', 'score'])]
            elif wrong_type == 'wrong subject':
                record['subject'] = random.choice(
                    ['MaTH', 'ENGlish', None, 123123, 2.4])
            elif wrong_type == 'invalid score':
                rand_score = random.random()
                if rand_score > 0.7:
                    record['score'] = random.randint(-1000, -1)
                elif rand_score > 0.3:
                    record['score'] = random.randint(100, 10000)
                else:
                    record['score'] = random.randint(0, 100) + random.random()  # use float point
            else:
                raise ValueError("impossible error type!")

            save_file(instance.action.config['savepath'], json.dumps(record))
        else:
            raise ValueError("impossible!")


if __name__ == '__main__':
    unittest.main(failfast=True)
