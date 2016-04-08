#!/usr/bin/env python
"""Python script to create a copy of global configs."""

import shutil
import os.path
import sys


def main():
    assert sys.version_info >= (3, 5), "you must have at least Python 3.5 to run this!"
    current_dir = sys.path[0]
    assert (os.path.isabs(current_dir))
    dir_to_copy_to = os.path.join(os.path.expanduser("~"), ".datasmart", 'config', 'core')
    if os.path.exists(dir_to_copy_to):
        print("old core config file exists! do you want to really remove them and use default ones?")
        answer = input("type y to confirm, otherwise the program will exit")
        if answer == 'y':
            shutil.rmtree(dir_to_copy_to)
        else:
            return

    def ignore_function(p, f):
        assert os.path.isabs(p)
        init_ignore_set = ['__pycache__', '__init__.py']
        for file in f:
            file_full = os.path.join(p, file)
            if os.path.isfile(file_full) and file != 'config.json':
                init_ignore_set.append(file)
        return list(init_ignore_set)

    assert not os.path.exists(dir_to_copy_to)
    os.makedirs(os.path.split(dir_to_copy_to)[0], exist_ok=True)  # make sure the top directory exists.
    shutil.copytree(os.path.join(current_dir, 'datasmart', 'config', 'core'), dir_to_copy_to,
                    ignore=ignore_function)
    print("done!")


if __name__ == '__main__':
    main()
