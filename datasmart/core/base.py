"""

core of DataSMART, defines basic config pass mechanism.

"""
from abc import ABC, abstractmethod

import datasmart.core.util.config
from . import global_config


class Base(ABC):
    """base class for all classes in DataSMART, primarily dealing with config loading.

    class variable `config_path` defines where to find the (JSON) config files for the class.

    """
    config_path = ('core', 'base')

    @abstractmethod
    def __init__(self, config=None) -> None:
        """ abstract constructor. force subclassing.

        users can pass in a config file in the constructor,
        and the class will use that.
        Otherwise, the class will find the config saved in locations defined by `config_path`, and postprocess it
        with (overriden) :func:`Base.normalize_config`.

        :return: None
        """
        assert self.config_path is not Base.config_path
        if config is None:
            # calling the __class__ to hint people to override with @staticmethod
            self.__config = self.__class__.normalize_config(datasmart.core.util.config.load_config(self.config_path))
        else:
            #  we allow you to do anything.
            self.__config = config

    @property
    def config_path(self) -> tuple:
        """return the class variable config path, read only.
        I create this simply to make sure that self.config_path can't be set.
        (well certainly you can set it if you really want).

        :return: the class variable config path, read only.
        """
        return self.__class__.config_path

    @property
    def class_identifier(self) -> str:
        return '[{}]'.format('.'.join(self.config_path))

    def set_config(self, config_new: dict) -> None:
        """ set new config, bypass postprocessing function :func:`Base.normalize_config`.

        :param config_new: new config to be set.
        :return: None
        """
        self.__config = config_new

    @property
    def config(self) -> dict:
        """returns a readonly version of the config (well you can definitely intentionally change config through methods
        provided by the config itself)...

        :return:
        """
        return self.__config

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
        #. ``root_package_spec``: how the system finds the datasmart package. Usually, it should be ``datasmart``
            but this is for the scenario where whole package is sub-packaged.

        :return: the global config.
        """
        return global_config
