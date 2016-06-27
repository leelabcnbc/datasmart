"""common mock related functions for test"""

from contextlib import ExitStack
from unittest import mock
from datasmart.core.action import Action
from . import file_util


class MockNames:
    git_repo_url = "datasmart.core.util.get_git_repo_url"
    git_repo_hash = "datasmart.core.util.get_git_repo_hash"
    git_check_clean = "datasmart.core.util.check_git_repo_clean"


def create_mocked_action(action_class: type, action_config=None, mock_options=None):
    if mock_options is None:
        mock_options = dict()

    # compute context managers added to mock managers
    with ExitStack() as stack:
        for key, value in mock_options.items():
            mock_contexts = parse_mock_option(key, value)
            for context in mock_contexts:
                stack.enter_context(context)
        if action_config is None:
            return action_class()
        else:
            return action_class(action_class.normalize_config(action_config))


def run_mocked_action(action: Action, mock_options=None):
    if mock_options is None:
        mock_options = dict()

    # compute context managers added to mock managers
    with ExitStack() as stack:
        for key, value in mock_options.items():
            mock_contexts = parse_mock_option(key, value)
            for context in mock_contexts:
                stack.enter_context(context)
        assert not action.is_prepared()
        action.run()
        assert action.is_finished()


def parse_mock_option(key: str, value: object):
    if key.startswith('custom'):
        return [value]
    elif key == 'input':
        return [mock.patch('builtins.input', side_effect=value)]
    elif key == 'git':
        return [mock.patch(MockNames.git_repo_url, return_value=value['git_url']),
                mock.patch(MockNames.git_repo_hash, return_value=value['git_hash']),
                mock.patch(MockNames.git_check_clean, return_value=True)]
    else:
        raise ValueError('unknown mock type!')


def setup_git_mock(*, git_repo_path=None):
    if git_repo_path is None:
        # use random path name if not specified.
        # ``git_repo_path`` should be set explicitly
        # when you really need to instantiate the repo, rather than only doing a mock.
        # TODO: make path generation better and introduce random url and hash as well.
        git_repo_path = " ".join(file_util.gen_filenames(3))
    return dict(git_url='http://git.example.com',
                git_hash='0000000000000000000000000000000000000000',
                git_repo_path=git_repo_path)
