import json
import jsonschema
from jsonschema import FormatChecker, Draft4Validator
from jsonschema.exceptions import ValidationError, SchemaError


def validate(schema, record):
    try:
        jsonschema.validate(instance=record, schema=schema, format_checker=FormatChecker(),
                            cls=Draft4Validator)
    except (ValidationError, SchemaError) as e:
        print(e)
        return False
    return True


def get_schema_string(schema):
    return json.dumps(schema.get_schema(ordered=True), indent=2)