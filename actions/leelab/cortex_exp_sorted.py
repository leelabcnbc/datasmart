"""DataSMART action for sorting raw cortex files"""

from datasmart.core.action import DBActionWithSchema
import jsl
import datasmart.core.schemautil as schemautil
from datasmart.actions.leelab.cortex_exp import CortexExpAction


class CortexExpSortedSchema(jsl.Document):
    cortex_exp_ref = jsl.StringField(format=schemautil.StringPatterns.bsonObjectIdPattern, required=True)
    sorted_files = jsl.DocumentField(format=schemautil.filetransfer.FileTransferSiteAndFileListRemote, required=True)
    sort_method = jsl.StringField(enum=['sacbatch_and_spikesort'], required=True)
    sort_config = jsl.StringField(required=True)  # arbitrary string to save the parameters for this sort
    timestamp = jsl.StringField(format="date-time", required=True)
    notes = jsl.StringField(required=True)


class CortexExpSortedAction(DBActionWithSchema):
    def get_schema_config(self):
        pass
        # maybe it's good to pass in the location of files, and scripts of the

    def generate_query_doc_template(self) -> str:
        pass

    table_path = ('leelab', 'cortex_exp_sorted')
    config_path = ('actions', 'leelab', 'cortex_exp_sorted')
    dbschema = CortexExpSortedSchema



    def __init__(self, config=None):
        super().__init__(config)

    def sites_to_remove(self, record):
        return record['sorted_files']['site']

    def is_stale(self, record, db_instance) -> bool:
        old_record_exist = db_instance[CortexExpAction.table_path[0]][CortexExpAction.table_path[1]].count(
            {"_id": record['cortex_exp_ref']})
        assert old_record_exist == 1 or old_record_exist == 0
        return old_record_exist == 0
