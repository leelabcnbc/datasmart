from datasmart.core.dbschema import DBSchema
from datasmart.core import util
from datasmart.core.action import ManualDBActionWithSchema
import jsl
from datasmart.core import schemautil


class FileUploadSchemaJSL(jsl.Document):
    schema_revision = jsl.IntField(enum=[1], required=True)  # the version of schema, in case we have drastic change
    timestamp = jsl.StringField(format="date-time", required=True)
    uploaded_files = jsl.DocumentField(schemautil.FileTransferSiteAndFileListRemote, required=True)
    notes = jsl.StringField(required=True)


class FileUploadSchema(DBSchema):
    schema_path = ('actions', 'demo', 'file_upload')

    def get_schema(self) -> dict:
        return FileUploadSchemaJSL.get_schema()

    def __init__(self, config=None):
        super().__init__(config)

    def post_process_record(self, record=None):
        record['timestamp'] = util.rfc3339_to_datetime(record['timestamp'])
        return record

    def post_process_template(self, template: str):
        template = template.replace("{{timestamp}}", util.current_timestamp())
        return template


class FileUploadAction(ManualDBActionWithSchema):
    table_path = ('demo', 'file_upload')
    config_path = ('actions', 'demo', 'file_upload')
    dbschema = FileUploadSchema

    def __init__(self, config=None):
        super().__init__(config)

    def sites_to_remove(self, record):
        return [record['uploaded_files']['site']]

    def custom_info(self) -> str:
        return "this is the class for upload files, please put all data you want under {}!".format(
            util.joinpath_norm(self.get_file_transfer_config()['local_data_dir'])
        )

    def get_schema_config(self):
        return {}

    def before_insert_record(self, record):
        """ upload files now!

        :param record:
        :return:
        """
        print("upload files begin...")
        ret = self.push_files(record['_id'], record['uploaded_files']['filelist'],
                              site=record['uploaded_files']['site'], relative=True)
        dest_site = ret['dest']
        print("upload files done... results saved in {} at {}/{}".format(
            dest_site['path'], dest_site['prefix'], dest_site['append_prefix']
        ))
        record['uploaded_files']['site'] = dest_site
        record['uploaded_files']['filelist'] = ret['filelist']
        assert schemautil.validate(schemautil.FileTransferSiteAndFileListRemoteAuto.get_schema(),
                                   record['uploaded_files'])
