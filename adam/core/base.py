"""

core of adam, defines basic config pass mechanism.

"""
from abc import ABC, abstractmethod
import os
import json
import pkgutil
from .. import global_config


class Base(ABC):
    """ base class for all classes in Adam, primarily dealing with config loading.
    """

    @abstractmethod
    def __init__(self) -> None:
        """ abstract constructor. force subclassing.

        :return: None
        """
        return

    def load_default_config(self, module_name: list) -> None:
        """  load config for a module. See doc for __load_config.
        :param module_name: module name as a list of strings, "AA.BB" is represented as ``["AA","BB"]``
        :return: None
        """
        self._config = self.normalize_config(self.__load_config(module_name))

    def set_config(self, config_new: dict) -> None:
        """ set new config, bypass postprocess.

        :param config_new: new config to be set.
        :return: None
        """
        self._config = config_new

    @property
    def config(self) -> dict:
        return self._config

    @staticmethod
    def normalize_config(config: dict) -> dict:
        """ postprocess config. Can be overriden to do some verification and normalization.

        :param config: preprocessed config file.
        :return: postprocessed config
        """
        return config

    @property
    def global_config(self) -> dict:
        """  global config of the package. not modifiable.

        Currently, there are only two fields.

        #. ``project_root``: the directory consisting the Python script being invoked.
        #. ``root_package_spec``: how the system finds the adam package. Usually, it should be ``neon``
            but this is for the scenario where whole package is sub-packaged.

        :return: the global config.
        """
        return global_config

    @staticmethod
    def __load_config(module_name: list) -> dict:
        """ load the config file for this module.

        It will perform the following steps:

        1. get the config file ``config/{os.sep.join(module_name)}/config.json``, where ``/`` is ``\`` for Windows,
           under the directory consisting the invoked Python script.
        2. if the above step fails, load the default one provided by the module.

        :param module_name: module name as a list of strings, "AA.BB" is represented as ``["AA","BB"]``
        :return: the JSON object of the module config file.
        """
        path_list = [global_config['project_root'], 'config'] + module_name + ['config.json']
        config_path = os.path.join(*path_list)
        if os.path.exists(config_path):
            with open(config_path, 'r') as config_stream:
                config = json.load(config_stream)
        else:
            # step 2. load default config
            config = json.loads(pkgutil.get_data(
                global_config['root_package_spec'] + '.config.' + '.'.join(module_name), 'config.json').decode())
        return config
