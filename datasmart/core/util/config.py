import json
import os
import pkgutil
from .io import load_file
from datasmart.core import global_config


def load_config(module_name: tuple, filename='config.json', load_json=True):
    """ load the config file for this module.

    It will perform the following steps:

    1. get the config file ``config/{os.sep.join(module_name)}/config.json``, where ``/`` is ``\`` for Windows,
       under the directory consisting the invoked Python script.
    2. if the above step fails, load the default one provided by the module.


    :param filename: which file to load. by default, ``config.json``.
    :param module_name: module name as a list of strings, "AA.BB" is represented as ``["AA","BB"]``
    :param load_json: whether parse the string as JSON or not.
    :return: the JSON object of the module config file, or the raw string.
    """
    path_list = (global_config['project_root'], 'config') + module_name + (filename,)
    config_path = os.path.join(*path_list)
    path_list_global = (os.path.expanduser('~'), '.datasmart', 'config') + module_name + (filename,)
    config_path_global = os.path.join(*path_list_global)
    a = os.path.exists(config_path)
    b = os.path.exists(config_path_global)
    if a or b:
        if a:
            # step 1. load config in current project.
            file_to_use = config_path
        else:
            # step 2. load config in ~/.datasmart
            file_to_use = config_path_global

        config = load_file(file_to_use, load_json=False)
    else:
        # step 3. load default config
        config = pkgutil.get_data(
            global_config['root_package_spec'] + '.config.' + '.'.join(module_name), filename).decode()
    if load_json:
        config = json.loads(config)
    return config
