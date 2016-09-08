import subprocess
import string
import re
from ..schemautil import stringpatterns

_sha1_checker = re.compile(stringpatterns.StringPatterns.sha1Pattern)


def get_cmd_output(cmds, cwd):
    result = subprocess.check_output(cmds, cwd=cwd).decode()
    for x in result:
        assert x in string.printable
    return result


def get_git_repo_url(repopath, remote_name='origin'):
    return get_cmd_output(['git', 'ls-remote', '--get-url', remote_name], cwd=repopath).strip()


def get_git_repo_hash(repopath):
    result = get_cmd_output(['git', 'rev-parse', '--verify', 'HEAD'], cwd=repopath).strip()
    assert _sha1_checker.fullmatch(result)
    return result


def check_git_repo_clean(repopath=None):
    if repopath is None:
        # from <http://stackoverflow.com/questions/957928/is-there-a-way-to-get-the-git-root-directory-in-one-command>
        repopath = subprocess.check_output(['git', 'rev-parse', '--show-toplevel']).decode().strip()
        print(repopath)
    git_status_output = get_cmd_output(['git', 'status', '--porcelain'], cwd=repopath)
    assert not git_status_output, "the repository must be clean!, check {}".format(git_status_output)
    return True

    # config['cortex_expt_repo_path']
    #     cortex_expt_repo_url =
    #


    # def check_unique_unicode_normalization(s: str) -> None:
    #     assert s == unicodedata.normalize('NFC', s) == unicodedata.normalize('NFD', s), "unique normalization must exist!"


def check_commit_in_remote(repopath, commit_sha1, remote_name='origin', remote_branch='master'):
    """check a certain commit is already in remote tracking branch `remote_name`/`remote_branch`.

    methods come from <http://stackoverflow.com/questions/1419623/how-to-list-branches-that-contain-a-given-commit>
    Parameters
    ----------
    repopath
    commit_sha1
    remote_name
    remote_branch

    Returns
    -------

    """
    assert _sha1_checker.fullmatch(commit_sha1), 'you must give a valid sha1'
    result_raw = get_cmd_output(['git', 'branch', '--no-color', '-r', '--contains', commit_sha1], cwd=repopath)
    # a space, then remote_name/remote_branch, then \n.
    #print(result_raw)
    return result_raw.find(' {}/{}\n'.format(remote_name, remote_branch)) != -1
