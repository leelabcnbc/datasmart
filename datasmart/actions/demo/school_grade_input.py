"""this is a demo action that shows manually typing of school records about grades of different subjects"""

import jsl
import datasmart.core.util.datetime
from datasmart.core.dbschema import DBSchema
from datasmart.core.action import ManualDBActionWithSchema

subjectlist = ["math", "english", "music", "drawing"]


class SchoolGradeJSL(jsl.Document):
    """class defining json schema for a school grade record.

    Here I recommend setting all fields to required, and optional fields are second-thought additions as you use more
    and more. Use of notes as an optional field is just a demonstration, and it's not recommended for new action.
    """
    timestamp = jsl.StringField(format="date-time", required=True)
    first_name = jsl.StringField(required=True)
    last_name = jsl.StringField(required=True)
    subject = jsl.StringField(enum=subjectlist, required=True)
    score = jsl.IntField(minimum=0, maximum=100, required=True)
    notes = jsl.StringField()


class SchoolGradeInputSchema(DBSchema):
    schema_path = ('actions', 'demo', 'school_grade_input')

    def get_schema(self) -> dict:
        return SchoolGradeJSL.get_schema()

    def __init__(self, config=None):
        super().__init__(config)

    def post_process_record(self, record=None) -> dict:
        # convert string-based timestamp to actual Python ``datetime`` object
        record['timestamp'] = datasmart.core.util.datetime.rfc3339_to_datetime(record['timestamp'])
        return record

    def post_process_template(self, template: str) -> str:
        template = template.replace("{{timestamp}}", datasmart.core.util.datetime.current_timestamp())
        return template


class SchoolGradeInputAction(ManualDBActionWithSchema):
    def sites_to_remove(self, record):
        return []

    def custom_info(self) -> str:
        return "this is the DataSMART action for saving grade data for an exam.\n" \
               "Please modify {} to your need".format(self.config['savepath'])

    def before_insert_record(self, record):
        super().before_insert_record(record)

    table_path = ('demo', 'school_grade_input')
    config_path = ('actions', 'demo', 'school_grade_input')
    dbschema = SchoolGradeInputSchema

    def __init__(self, config=None):
        super().__init__(config)

    def get_schema_config(self):
        return {}
