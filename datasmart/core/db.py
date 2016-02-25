"""

The module for database handling in adam.

"""

from pymongo import MongoClient
from .base import Base


class DB(Base):
    """
    the class for interacting with database.

    It handles authentication, and provides a MongoClient instance for CRUD operations.
    """
    config_path = ('core', 'db')

    def __init__(self, config=None):
        """ constructor for DB class.
        It will perform the following steps:

        1. get the config file ``config/db/config.json`` under the directory consisting the invoked Python script.
        2. if the above step fails, load the default one:
            .. literalinclude:: /../datasmart/config/core/db/config.json
                :language: json

        :return: None
        """
        super().__init__(config)
        self.client_instance = None

    def connect(self):
        """ connect MongoDB and set client_instance.

        if will connect to database based on the config and set ``self.client_instance``
        to the MongoClient instance created.

        :return: None
        """
        assert self.client_instance is None

        # step 3. connect to database
        client = MongoClient(self.config['url'], self.config['port'])
        # TODO: MongoClient is nonblocking, and auth is blocking.
        # which means that if there's no auth, this method can return yet no db is available.
        if self.config['authentication']:
            client[self.config['auth_db']].authenticate(name=self.config['user'], password=self.config['password'])
        self.client_instance = client

    def disconnect(self):
        """ disconnect MongoDB.

        :return: None
        """
        self.client_instance.close()
        self.client_instance = None
