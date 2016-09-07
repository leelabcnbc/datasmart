import os
import random
import string
import shutil
import time

import datasmart
import datasmart.core   # without this, if we call gen_filename without import datasmart.core elsewhere, it will fail
# I think datasmart object is shared across everything.

from . import fake


def gen_filename_inner(word_len):
    return (''.join(random.choice(""" !"#:$%&'()*+,-;<=>?@[\]^_`{|}~""" + string.ascii_letters) for _ in
                    range(word_len)) + fake.file_extension()).strip()


def gen_filename():
    """ generate a single file name, avoiding all keywords in datasmart ('_data' for filetransfer during testing).

    avoiding reserved file names in datasmart.

    :return:
    """
    word_len = random.randint(1, 20)

    candidate = gen_filename_inner(word_len=word_len)
    while any([(candidate in kw) for kw in datasmart.core.keywords]):
        # here, we use substring match, as query template and prepare result are now fully qualified.
        candidate = gen_filename_inner(word_len=word_len)
    return candidate


def gen_filename_strict_lower_inner(word_len):
    return (''.join(random.choice("abcdefghijklmnopqrstuvwxyz_-0123456789") for _ in
                    range(word_len)) + fake.file_extension()).strip()


def gen_filename_strict_lower(different_from=None):
    word_len = random.randint(1, 20)
    if different_from is None:
        different_from = []
    candidate = gen_filename_strict_lower_inner(word_len)
    while candidate in different_from:
        candidate = gen_filename_strict_lower_inner(word_len)
    return candidate


def gen_filenames(n=100):
    filenames = set()
    while len(filenames) < n:
        filenames.add(gen_filename())
    return list(filenames)


def _gen_dirs(n=None, abs_path=True):
    if n is None:
        n = random.randint(0, 3)
    assert n >= 0
    abs_char = os.sep if abs_path else ""
    if n == 0:
        return os.path.normpath(abs_char)
    else:
        return os.path.normpath(os.path.join(*([abs_char] + gen_filenames(n=n))))


def gen_unique_local_paths(n):
    result = set()
    while len(result) < n:
        new_dir_name = _gen_dirs(n=1, abs_path=False)
        if not os.path.exists(new_dir_name):
            result.add(new_dir_name)
    return list(result)


def gen_filelist(n=100, abs_path=True):
    assert n >= 0
    filelist = gen_filenames(n)
    filelist = [os.path.normpath(os.path.join(_gen_dirs(abs_path=abs_path), x)) for x in filelist]
    return filelist


def create_dirs_from_dir_list(dir_list):
    for dir in dir_list:
        os.makedirs(dir)


def rm_dirs_from_dir_list(dir_list):
    for dir in dir_list:
        assert os.path.isdir(dir)
        shutil.rmtree(dir)
    time.sleep(0.25)  # buffer time for removal
    for dir in dir_list:
        assert not os.path.exists(dir), "dir {} still exist".format(dir)


def rm_files_from_file_list(file_list, must_exist=True):
    for file in file_list:
        if must_exist or os.path.exists(file):
            assert os.path.isfile(file)
            os.remove(file)
    time.sleep(0.25)  # buffer time for removal
    for file in file_list:
        assert not os.path.exists(file), "file {} still exist".format(file)


def create_files_from_filelist(filelist, local_data_dir, subdirs_this=None):
    if subdirs_this is None:
        subdirs_this = []
    for file in filelist:
        file_path = os.path.join(*([local_data_dir] + subdirs_this + [file]))
        os.makedirs(os.path.dirname(file_path), exist_ok=True)  # exist is possible although very unlikely.
        if os.path.exists(file_path):
            print("{} exist!".format(file_path))
        assert not os.path.exists(file_path)
        with open(file_path, 'w') as f:
            f.writelines(fake.sentences())


if __name__ == '__main__':
    print(gen_filelist(10))
