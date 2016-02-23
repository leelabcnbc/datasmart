from textwrap import dedent
import json
from jsonschema import validate, FormatChecker, Draft4Validator
from jsonschema.exceptions import ValidationError, SchemaError


"""
schema: schema in Python dictionary, created by json.loads(schema_doc)
schema_doc: string version of schema, in JSON format.
template: string version of a doc valid under the schema.
record: a doc valid under the schema as a Python dictionary.
"""


class RecordSchema:

    def __init__(self):
        # validate the schema
        # if fail, will raise Error.
        if self.schema_doc() is not None:
            Draft4Validator.check_schema(self.get_schema())

    def get_schema(self):
        return json.loads(self.schema_doc())

    def get_template(self):
        processed_template = self.get_template_inner()
        # remove leading spaces.
        processed_template = dedent(processed_template).strip()
        # make sure that the template can at least pass the test.
        assert self.validate_record(json.loads(processed_template))
        return processed_template

    def validate_record(self, record):
        # this will raise error if there's problem
        try:
            validate(instance=record, schema=self.get_schema(), format_checker=FormatChecker(),
                     cls=Draft4Validator)
        except (ValidationError, SchemaError) as e:
            print(e)
            return False
        return True

    def generate_record(self, template):
        # validate (string) record using the schema
        record = json.loads(template)
        assert self.validate_record(record)
        # post process to make it ready to be pushed
        self.post_process_record(record)
        return record

    # please override the the following methods.
    def get_template_inner(self):
        raise NotImplementedError

    def where_to_insert(self):
        """
        :return: the (db, collection) pair into which the document should be inserted.
        """
        raise NotImplementedError

    def schema_doc(self):
        return None  # should return a string being the schema.

    def post_process_record(self, record=None):
        """
        :param record: a Python dictionary of record
        :return: a Python dictionary ready to be inserted to DB.
        This is required for particular kinds of data types, such as date.
        """
        pass
