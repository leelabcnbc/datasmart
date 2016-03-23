from datasmart.core.dbschema import DBSchema
from datasmart.core import util
from datasmart.core.action import DBAction
import jsl


class FileDownloadAction(DBAction):
    table_path = ('demo', 'file_download')
    config_path = ('actions', 'demo', 'file_download')

    def __init__(self, config=None):
        super().__init__(config)

    def generate_query_doc_template(self) -> str:
        return util.load_config(self.__class__.config_path, 'query_template.py', load_json=False)
