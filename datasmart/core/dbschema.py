import json
from jsonschema import Draft4Validator
from abc import ABC, abstractmethod
from . import util
from . import schemautil


class DBSchema(ABC):
    """
    schema: schema in Python dictionary,
    template: string version of a doc valid under the schema.
    record: a dict ready to be inserted to MongoDB

    """
    schema_path = ('actions', '<None>')

    @abstractmethod
    def __init__(self, config=None):
        # check that schema_path is already overloaded.
        assert self.schema_path is not DBSchema.schema_path
        # validate the schema
        # if fail, will raise Error.
        Draft4Validator.check_schema(self.get_schema())
        self.config = config

    @property
    def schema_path(self) -> tuple:
        return self.__class__.schema_path

    #  override the following two methods post_process_template and post_process_record
    @abstractmethod
    def post_process_template(self, template: str) -> str:
        """ post processing of the raw template string.

        :param template:
        :return:
        """
        return template

    @abstractmethod
    def post_process_record(self, record: dict) -> dict:
        """ post processing of a record to be inserted.

        :param record: a Python dictionary of record
        :return: a Python dictionary ready to be inserted to DB.

        This is required for particular kinds of data types, such as date,
        which are in different formats for JSON schema and Mongo.
        """
        return record

    # should not change get_schema, get_template, validate_record, and generate_record
    def get_schema(self) -> dict:
        """
        :return: the dictionary of a JSON schema.
        """
        return util.load_config(self.schema_path, 'schema.json')

    def get_template(self) -> str:
        """ this is only useful if you are going to manually type in the template.

        :return: the **string** of a JSON document.
        """
        template_base = util.load_config(self.schema_path, 'template.json', load_json=False)
        processed_template = self.post_process_template(template_base)
        assert self.validate_record(json.loads(processed_template))
        return processed_template

    def validate_record(self, record) -> bool:
        # this will raise error if there's problem
        return schemautil.validate(self.get_schema(), record)

    def generate_record(self, record):
        # validate record using the schema
        assert self.validate_record(record)
        # post process to make it ready to be pushed
        return self.post_process_record(record)
