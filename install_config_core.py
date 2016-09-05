#!/usr/bin/env python
"""Python script to create a copy of global configs.

It's assumed that datasmart project must be importable through `datasmart` (not a submodule)
"""

import shutil
import os.path
import sys
from datasmart.config.core import __path__ as pkg_to_copy_from_path
import pkgutil


def main():
    assert sys.version_info >= (3, 5), "you must have at least Python 3.5 to run this!"
    # current_dir = sys.path[0]
    # assert (os.path.isabs(current_dir))
    dir_to_copy_to = os.path.join(os.path.expanduser("~"), ".datasmart", 'config', 'core')
    if os.path.exists(dir_to_copy_to):
        print("old core config file exists! do you want to really remove them and use default ones?")
        answer = input("type y to confirm, otherwise the program will exit")
        if answer == 'y':
            shutil.rmtree(dir_to_copy_to)
        else:
            return
    core_pkgs_to_copy_names = [x[1] for x in pkgutil.iter_modules(pkg_to_copy_from_path)]
    print(core_pkgs_to_copy_names)
    core_pkgs_to_copy_filecontent = []
    # for each one, copy its config.json
    print('in total {} packages to work on.'.format(len(core_pkgs_to_copy_names)))
    for pkg in core_pkgs_to_copy_names:
        # read out the content of config file.
        pkg_full = 'datasmart.config.core.' + pkg
        content_this = pkgutil.get_data(pkg_full, 'config.json')
        assert content_this is not None, "config file for {} does not exist!".format(pkg_full)
        core_pkgs_to_copy_filecontent.append(content_this)

    assert not os.path.exists(dir_to_copy_to)
    os.makedirs(dir_to_copy_to)  # create all intermediate ones if necessary.

    for idx, (pkg, content) in enumerate(zip(core_pkgs_to_copy_names, core_pkgs_to_copy_filecontent), start=1):
        pkg_dir = os.path.join(dir_to_copy_to, pkg)
        pkg_config_path = os.path.join(pkg_dir, 'config.json')
        os.mkdir(pkg_dir)
        with open(pkg_config_path, 'wb') as f_this:
            f_this.write(content)
        print('{}/{}: {} done'.format(idx, len(core_pkgs_to_copy_names), pkg))

    print("done!")


if __name__ == '__main__':
    main()
