import subprocess


def get_cmd_output(cmds, cwd):
    return subprocess.check_output(cmds, cwd=cwd).decode().strip()


def get_git_repo_url(repopath):
    return get_cmd_output(['git', 'ls-remote', '--get-url', 'origin'], cwd=repopath)


def get_git_repo_hash(repopath):
    return get_cmd_output(['git', 'rev-parse', '--verify', 'HEAD'], cwd=repopath)


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
