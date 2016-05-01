#!/usr/bin/env python
"""Python script to create a copy of global configs."""

import shutil
import os
import stat
import sys


def main(install_folder, actions):
    def ignore_function(p, f):
        assert os.path.isabs(p)
        init_ignore_set = ['__pycache__', '__init__.py']
        for file in f:
            file_full = os.path.join(p, file)
            if os.path.isfile(file_full) and file != 'config.json':
                init_ignore_set.append(file)
        return list(init_ignore_set)

    current_dir = sys.path[0]
    assert os.path.isabs(current_dir)
    assert not os.path.exists(install_folder), 'the installation folder must not exist!'
    os.makedirs(install_folder)
    os.makedirs(os.path.join(install_folder, 'config', 'actions'))
    assert os.path.exists(install_folder)
    for action in actions:
        action_file = os.path.join(current_dir, 'datasmart', 'actions', action) + '.py'
        action_config_dir = os.path.join(current_dir, 'datasmart', 'config', 'actions', action)
        action_script_file = os.path.join(current_dir, 'demo_scripts', 'actions', action) + '.py'
        assert os.path.isfile(action_file), "action {} doesn't exist!".format(action)
        assert os.path.isdir(action_config_dir), "action config dir doesn't exist! should be a bug"
        assert os.path.isfile(action_script_file), "action demo script doesn't exist! should be a bug"

    for action in actions:
        action_flat_name = "_".join(action.split('/'))
        action_config_dir = os.path.join(current_dir, 'datasmart', 'config', 'actions', action)
        action_config_dir_new = os.path.join(install_folder, 'config', 'actions', action)
        assert os.path.isdir(action_config_dir), "action config dir doesn't exist! should be a bug"
        os.makedirs(os.path.split(action_config_dir_new)[0], exist_ok=True)
        shutil.copytree(action_config_dir, action_config_dir_new, ignore=ignore_function)

        # copy the demo script to action_flat_name
        action_script_file = os.path.join(current_dir, 'demo_scripts', 'actions', action) + '.py'
        shutil.copyfile(action_script_file, os.path.join(install_folder, action_flat_name + '.py'))
        # create a bash script to start it.
        bash_script = os.path.join(install_folder, 'start_' + action_flat_name + '.sh')
        with open(bash_script, 'wt', encoding='utf-8') as f:
            f.write('#!/usr/bin/env bash\n')
            f.write('. activate datasmart\n')
            f.write('export PYTHONPATH={}:PYTHONPATH\n'.format(current_dir))
            f.write('python {}\n'.format(action_flat_name + '.py'))
        # add executable bit to the file.
        os.chmod(bash_script, stat.S_IEXEC | os.stat(bash_script).st_mode)


if __name__ == '__main__':
    assert len(sys.argv) >= 3, "at least 2 arguments!"
    assert sys.version_info >= (3, 5), "you must have at least Python 3.5 to run this!"
    main(sys.argv[1], sys.argv[2:])
