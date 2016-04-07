import json
import jsonschema
from jsonschema import FormatChecker, Draft4Validator


def validate(schema, record):
    jsonschema.validate(instance=record, schema=schema, format_checker=FormatChecker(),
                        cls=Draft4Validator)

    return True


def get_schema_string(schema):
    return json.dumps(schema.get_schema(ordered=True), indent=2)