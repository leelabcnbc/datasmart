"""DataSMART action for uploading metadata about a mouse experiment in Sandra Kuhlman's lab.
Format of a database record for this action.

.. literalinclude:: /../datasmart/config/actions/klab/mouse_exp/template.json
   :language: json

"""

import jsl

from datasmart.core import schemautil
from datasmart.core.action import ManualDBActionWithSchema
from datasmart.core.dbschema import DBSchema
from datasmart.core.util import util_old


class MouseExpSchemaJSL(jsl.Document):
    """class defining json schema for a database record. See top of file"""
    schema_revision = jsl.IntField(enum=[1], required=True)  # the version of schema, in case we have drastic change
    timestamp = jsl.StringField(format="date-time", required=True)
    animal_id = jsl.StringField(required=True)  # TODO: any specific format?  # should check another database.
    session_name = jsl.StringField(required=True)  # TODO: any specific format?  is this unique?
    experiment_name = jsl.StringField(required=True)
    # TODO: only one file?
    # 2) in dataSmart_Example.txt
    isi_map_data = jsl.DocumentField(schemautil.filetransfer.FileTransferSiteAndFileListRemote, required=True)
    # 3) in dataSmart_Example.txt
    master_alignment = jsl.DocumentField(schemautil.filetransfer.FileTransferSiteAndFileListRemote, required=True)
    # 4) in dataSmart_Example.txt
    raw_data = jsl.DocumentField(schemautil.filetransfer.FileTransferSiteAndFileListRemote, required=True)
    real_time_rf_data = jsl.DocumentField(schemautil.filetransfer.FileTransferSiteAndFileListRemote, required=True)
    # maybe this is for Excel tally?
    notes = jsl.StringField(required=True)


class MouseExpSchema(DBSchema):
    schema_path = ('actions', 'klab', 'mouse_exp')

    def get_schema(self) -> dict:
        return MouseExpSchemaJSL.get_schema()

    def __init__(self, config=None):
        super().__init__(config)

    def post_process_record(self, record=None) -> dict:
        """ add file hash, check file exists.

        :param record: the record input by the user and validated against the schema.
        :return: the final record to be inserted.
        """
        # convert string-based timestamp to actual Python ``datetime`` object
        record['timestamp'] = util_old.rfc3339_to_datetime(record['timestamp'])
        return record

    def post_process_template(self, template: str) -> str:
        template = template.replace("{{timestamp}}", util_old.current_timestamp())
        return template


class MouseExpAction(ManualDBActionWithSchema):
    def sites_to_remove(self, record):
        return []

    def custom_info(self) -> str:
        return "this is the DataSMART action for saving metadata for a mouse experiment in klab.\n" \
               "Please modify {} to your need".format(self.config['savepath'])

    def before_insert_record(self, record):
        # check unique session_name.

        # fields to check
        field_to_check = ['isi_map_data', 'master_alignment', 'raw_data', 'real_time_rf_data']

        for field in field_to_check:
            print("check that files for {} are really there...".format(field))
            site = record[field]['site']
            filelist = record[field]['filelist']
            ret = self.check_file_exists(site, filelist, unique=True)
            # use normalized names
            record[field]['site'] = ret['src']
            record[field]['filelist'] = ret['filelist']

        assert self.check_field_count(field_name='session_name',
                                      field_value=record['session_name']) == 0, "unique session name!"

    table_path = ('klab', 'mouse_exp')
    config_path = ('actions', 'klab', 'mouse_exp')
    dbschema = MouseExpSchema

    def __init__(self, config=None):
        super().__init__(config)

    def get_schema_config(self):
        return {}
