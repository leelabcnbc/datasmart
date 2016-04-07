import os
import random
from faker import Factory
import string

fake = Factory.create()


def gen_filename():
    word_len = random.randint(1, 20)
    return (''.join(random.choice(""" !"#:$%&'()*+,-;<=>?@[\]^_`{|}~""" + string.ascii_letters) for _ in
                   range(word_len)) + fake.file_extension()).strip()


def gen_filenames(n=100):
    filenames = set()
    while len(filenames) < n:
        filenames.add(gen_filename())
    return list(filenames)


def gen_dirs(n=None, abs_path=True):
    if n is None:
        n = random.randint(0, 3)
    assert n >= 0
    abs_char = os.sep if abs_path else ""
    if n == 0:
        return os.path.normpath(abs_char)
    else:
        return os.path.normpath(os.path.join(*([abs_char] + gen_filenames(n=n))))


def gen_filelist(n=100, abs_path=True):
    assert n >= 0
    filelist = gen_filenames(n)
    filelist = [os.path.normpath(os.path.join(gen_dirs(abs_path=abs_path), x)) for x in filelist]
    return filelist


def create_files_from_filelist(filelist, local_data_dir, subdirs_this=None):
    if subdirs_this is None:
        subdirs_this = []
    for file in filelist:
        file_path = os.path.join(*([local_data_dir] + subdirs_this + [file]))
        os.makedirs(os.path.dirname(file_path), exist_ok=True)  # exist is possible although very unlikely.
        assert not os.path.exists(file_path)
        with open(file_path, 'w') as f:
            f.writelines(fake.sentences())


class MockNames:
    git_repo_url = "datasmart.core.util.get_git_repo_url"
    git_repo_hash = "datasmart.core.util.get_git_repo_hash"
    git_check_clean = "datasmart.core.util.check_git_repo_clean"



if __name__ == '__main__':
    print(gen_filelist(10))
