import os
import random
from faker import Factory

fake = Factory.create()

def gen_filename():
    if random.random() < 0:
        return fake.sentence() + fake.file_extension()
    else:
        return ''.join(random.choice("""!"#:$%&'()*+,-;<=>?@[\]^_`{|}~""") for _ in range(10))


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
        return os.path.normpath(os.path.join(*([abs_char] + [x[:-1] for x in fake.sentences(nb=n)])))


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


if __name__ == '__main__':
    print(gen_filelist(10))
