"""

core of adam, defines basic config pass mechanism.

"""
from abc import ABC, abstractmethod
from .. import global_config
from . import util

class Base(ABC):
    """ base class for all classes in Adam, primarily dealing with config loading.
    """
    config_path = ('core','Base')

    @abstractmethod
    def __init__(self) -> None:
        """ abstract constructor. force subclassing.

        :return: None
        """
        assert self.config_path is not Base.config_path
        self._config = self.normalize_config(util.load_config(self.config_path))

    @property
    def config_path(self) -> tuple:
        return self.__class__.config_path

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
        #. ``root_package_spec``: how the system finds the datasmart package. Usually, it should be ``neon``
            but this is for the scenario where whole package is sub-packaged.

        :return: the global config.
        """
        return global_config

