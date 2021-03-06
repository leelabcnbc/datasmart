"""
The module for database handling in DataSMART.
"""

from pymongo import MongoClient
from .base import Base


class DB(Base):
    """
    the class for interacting with database.

    It handles authentication, and provides a MongoClient instance for CRUD operations.
    """
    config_path = ('core', 'db')

    def __init__(self, config: dict = None) -> None:
        """ constructor for DB class.
        It will load the default config using the base class constructor,
        and init the client_instance to None, which will hold connected MongoDB client later.

        :return: None
        """
        super().__init__(config)
        self.client_instance = None

    def connect(self):
        """ connect MongoDB and set client_instance.

        it will set ``self.client_instance`` to the MongoClient instance created.

        :return: None
        """
        # we can't reconnect.
        assert self.client_instance is None
        # step 3. connect to database
        client = MongoClient(self.config['url'], self.config['port'], j=True)  # force journaling.
        # oldTODO: MongoClient is nonblocking, and auth is blocking. So if there's no auth, we don't discover bug
        # well not the case. it will stop after 20 seconds by default.
        # until much later.
        # which means that if there's no auth, this method can return yet no db is available.
        # assert self.config['authentication'], "DB must be connected with authentication!"
        if self.config['authentication']:
            # this line would raise exception if authentication fails.
            client[self.config['auth_db']].authenticate(name=self.config['user'], password=self.config['password'])
        self.client_instance = client

    def disconnect(self):
        """ disconnect MongoDB.

        :return: None
        """
        # by calling .close(), we implicit make sure client_instance is not None.
        self.client_instance.close()
        self.client_instance = None


class DBContextManager:
    def __init__(self, db_instance: DB):
        self.__db_instance = db_instance

    def __enter__(self):
        assert self.__db_instance.client_instance is None
        self.__db_instance.connect()
        return self.__db_instance

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.__db_instance.disconnect()
        assert self.__db_instance.client_instance is None
        if exc_type is None:
            return True
