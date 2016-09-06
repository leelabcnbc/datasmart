#!/usr/bin/env python
"""Python script to install datasmart actions.

It's assumed that datasmart project must be importable through `datasmart` (not a submodule)
"""

import shutil
import os
from datasmart.config.core import __path__ as pkg_to_copy_from_path
import sys
import pkgutil
import json
import datasmart
import stat

help_string = """Usage:
{exec} /project/upload demo/file_upload  # install action `file_upload` from lab `demo`, under dir `/project/upload`
{exec} /project/mixed lab1/action1 lab2/action2  # install two actions from two labs, under dir `/project/mixed`

Project directory and at least one action must be specified.
"""

core_pkgs_names = [x[1] for x in pkgutil.iter_modules(pkg_to_copy_from_path)]
datasmart_path = [os.path.split(x)[0] for x in datasmart.__path__]


def check_one_meta(meta_dict):
    assert 'action_name' in meta_dict
    assert 'revocable' in meta_dict
    assert set(meta_dict.keys()) <= {'override_core_config', 'override_start_script',
                                     'action_name',
                                     'revocable'}


def construct_start_script(action_module, action_module_config, meta_this):
    if 'override_start_script' in meta_this:
        start_script_content = pkgutil.get_data(action_module_config, meta_this['override_start_script'])
    else:
        start_script_1_import = "from {} import {}".format(action_module, meta_this['action_name'])
        if meta_this['revocable']:
            start_script_2_run = """
if __name__ == '__main__':
    a = {}()
    test = input('enter to run, and enter anything then enter to revoke.')
    if not test:
        a.run()
    else:
        a.revoke()
""".format(meta_this['action_name'])
        else:
            start_script_2_run = """
if __name__ == '__main__':
    a = {}()
    test = input('enter to run, and enter anything then enter to exit.')
    if not test:
        a.run()
""".format(meta_this['action_name'])
        start_script_content = (start_script_1_import + '\n' + start_script_2_run).encode()
    return start_script_content


def generate_config_override(action_module_config, meta_this):
    result = {}
    if 'override_core_config' in meta_this:
        for module_name, config_file_for_this in meta_this['override_core_config'].items():
            assert module_name in core_pkgs_names
            config_file_this_content = pkgutil.get_data(action_module_config, config_file_for_this)
            assert config_file_this_content is not None
            result[module_name] = config_file_this_content
    return result


def generate_wrapper_script(action_flat_name):
    template = """#!/usr/bin/env bash
. activate datasmart
# it would be a very bad idea if you have space in your names
export PYTHONPATH={datasmart_path}:$PYTHONPATH
python {start_script_name}
""".format(datasmart_path=':'.join(datasmart_path),
           start_script_name=action_flat_name + '.py')
    return template.encode()


def main(install_folder, actions):
    modified_core_list = set()

    assert sys.version_info >= (3, 5), "you must have at least Python 3.5 to run this!"
    if os.path.exists(install_folder):
        print("old project folder `{}` exists! do you want to really remove them and create a new one?"
              " potentially all existing data there will be lost.".format(install_folder))
        answer = input("type y to confirm, otherwise the program will exit")
        if answer == 'y':
            shutil.rmtree(install_folder)
        else:
            return
    assert not os.path.exists(install_folder), 'the installation folder must not exist!'
    os.makedirs(install_folder)
    action_config_dir_root = os.path.join(install_folder, 'config', 'actions')
    core_config_dir_root = os.path.join(install_folder, 'config', 'core')
    assert os.path.exists(install_folder)

    for action in actions:
        action_components = action.split('/')
        action_module = 'datasmart.actions.' + '.'.join(action_components)
        print('working on {} ... '.format(action_module), end='')
        action_module_config = 'datasmart.config.actions.' + '.'.join(action_components)
        meta_file_this = pkgutil.get_data(action_module_config, '_dm_meta_.json')
        # ok. time to collect their meta file.
        assert meta_file_this is not None
        meta_this = json.loads(meta_file_this.decode())

        # TODO: a json schema based checking, rather than adhoc.
        check_one_meta(meta_this)
        # collect config for this action.
        config_this_action = pkgutil.get_data(action_module_config, 'config.json')
        # then collect config overrides
        config_override_dict_this = generate_config_override(action_module_config, meta_this)
        # content of start script.
        start_script_content = construct_start_script(action_module, action_module_config, meta_this)
        # content of wrapper script.
        action_flat_name = '_'.join(action_components)
        assert ('.' not in action_flat_name) and (' ' not in action_flat_name)
        wrapper_script_content = generate_wrapper_script(action_flat_name)

        # write action config
        action_config_dir_this = os.path.join(action_config_dir_root, *action_components)
        os.makedirs(action_config_dir_this)
        with open(os.path.join(action_config_dir_this, 'config.json'), 'wb') as f_config:
            f_config.write(config_this_action)

        # write config overrides
        for core_module_name, core_module_config in config_override_dict_this.items():
            modified_core_list.add(core_module_name)
            core_config_dir_this = os.path.join(core_config_dir_root, core_module_name)
            if os.path.exists(core_config_dir_this):
                print('warning, config for core.{} already exists. old config get overwritten'.format(core_module_name))
            else:
                os.makedirs(core_config_dir_this)
                with open(os.path.join(core_config_dir_this, 'config.json'), 'wb') as f_config:
                    f_config.write(core_module_config)

        # write start script
        with open(os.path.join(install_folder, action_flat_name + '.py'), 'wb') as f_start_script:
            f_start_script.write(start_script_content)
        # write wrapper script
        wrapper_script_name = os.path.join(install_folder, 'start_' + action_flat_name + '.sh')
        with open(wrapper_script_name, 'wb') as f_wrapper_script:
            f_wrapper_script.write(wrapper_script_content)
        os.chmod(wrapper_script_name, stat.S_IEXEC | os.stat(wrapper_script_name).st_mode)
        print('done')
    if modified_core_list:
        print('config for core modules {} got overriden. Check them under {}'.format(modified_core_list,
                                                                                     core_config_dir_root))


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print(help_string.format(exec=sys.argv[0]))
        sys.exit(1)
    main(sys.argv[1], sys.argv[2:])
