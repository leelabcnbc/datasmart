"""DataSMART action for sorting raw cortex files"""

from datasmart.core.action import DBActionWithSchema, save_wait_and_load
from datasmart.core.dbschema import DBSchema
import jsl
import datasmart.core.schemautil as schemautil
from datasmart.actions.leelab.cortex_exp import CortexExpAction
from datasmart.core import util
from bson import ObjectId
from collections import OrderedDict
import json
from copy import deepcopy

sort_methods = ['sacbatch_and_spikesort']


class CortexExpSortedQueryResultSchemaJSL(jsl.Document):
    cortex_exp_ref = jsl.StringField(pattern=schemautil.StringPatterns.bsonObjectIdPattern, required=True)
    files_to_sort = jsl.DocumentField(schemautil.filetransfer.FileTransferSiteAndFileListRemote, required=True)


class CortexExpSortedSchemaJSL(jsl.Document):
    cortex_exp_ref = jsl.StringField(format=schemautil.StringPatterns.bsonObjectIdPattern, required=True)
    files_to_sort = jsl.DocumentField(schemautil.filetransfer.FileTransferSiteAndFileListRemote, required=True)
    sorted_files = jsl.DocumentField(schemautil.filetransfer.FileTransferSiteAndFileListRemoteAuto, required=True)
    sort_method = jsl.StringField(enum=sort_methods, required=True)
    sort_config = jsl.DictField(required=True)  # arbitrary dict to save the parameters for this sort.
    sort_person = jsl.StringField(enum=["Ge Huang", ], required=True)  # who sorted.
    timestamp = jsl.StringField(format="date-time", required=True)
    notes = jsl.StringField(required=True)


class CortexExpSortedSchema(DBSchema):
    schema_path = ('actions', 'leelab', 'cortex_exp_sorted')

    def get_schema(self) -> dict:
        return CortexExpSortedSchemaJSL.get_schema()

    def __init__(self, config=None):
        super().__init__(config)

    def post_process_record(self, record=None) -> dict:
        # convert string-based timestamp to actual Python ``datetime`` object
        record['timestamp'] = util.rfc3339_to_datetime(record['timestamp'])
        return record

    def post_process_template(self, template: str) -> str:
        return template


class CortexExpSortedAction(DBActionWithSchema):
    def perform(self) -> None:
        for idx, method in enumerate(sort_methods, start=1):
            print("{}: {}".format(idx, method))
        sort_choice_idx = int(
            input("please choose the method to do sorting, from {} to {}".format(1, len(sort_methods))))
        assert 1 <= sort_choice_idx <= len(sort_methods), "invalid method!"
        sort_choice = sort_methods[sort_choice_idx - 1]
        input("press enter to start using method {}".format(sort_choice))
        record_candidate = self.generate_init_record(sort_choice)
        if sort_choice == 'sacbatch_and_spikesort':
            record_candidate = self.perform_sacbatch_and_spikesort(record_candidate)
        else:
            raise ValueError('impossible!')
        record_candidate = self.dbschema_instance.generate_record(record_candidate)
        record_candidate['_id'] = self.prepare_result['result_ids'][0]
        self.insert_results([record_candidate])
        print("done!")


    def generate_init_record(self, sort_choice):
        sorted_files = deepcopy(self.prepare_result['files_to_sort'])
        sorted_files['site']['append_prefix'] = '.'
        record = OrderedDict([
            ('cortex_exp_ref', self.prepare_result['cortex_exp_ref']),
            ('files_to_sort', self.prepare_result['files_to_sort']),
            ('sorted_files', sorted_files),
            ('sort_method', sort_choice),
            ('sort_config', {}),
            ('sort_person', 'Ge Huang'),
            ('timestamp', util.current_timestamp()),
            ('notes', '')
        ])
        assert self.dbschema_instance.validate_record(record)
        return record

    def perform_sacbatch_and_spikesort(self, record):
        insert_id = self.prepare_result['result_ids'][0]
        record = save_wait_and_load(json.dumps(record, indent=2),
                                    self.config['savepath'],
                                    "please edit files to sort in 'files_to_sort', "
                                    "and edit notes and sort person. don't "
                                    "care about sorted_files now...", overwrite=False, load_json=True)
        # first, keep only NEV files
        assert self.dbschema_instance.validate_record(record)
        for file in record['files_to_sort']['filelist']:
            assert file.lower().endswith('.nev'), "only NEV files are supported!"

        print("now {} NEV files will be downloaded to {}".format(
            len(record['files_to_sort']['filelist']),
            self.get_file_transfer_config()['local_data_dir']
        ))
        input("press enter to continue")
        ret = self.fetch_files(record['files_to_sort']['filelist'], record['files_to_sort']['site'],
                               relative=False, local_fetch_option='copy')
        filelist_local = ret['filelist']



        # now time to write a script for sac batch.
        prompt_text = "SAC script {} and SpikeSort script {} are in {}, run them outside and then press enter".format(
            "sac_{}.m".format(str(insert_id)), "spikesort_{}.m".format(str(insert_id)),
            self.get_file_transfer_config()['local_data_dir']
        )
        #TODO insert the raw script for SAC and SpikeSort into
        input(prompt_text)
        input("press again if you are really sure you are finished.")
        print("now {} sorted NEV files will be uploaded")
        ret_2 = self.push_files(insert_id, filelist_local, relative=False)
        record['sorted_files']['site'] = ret_2['dest']
        record['sorted_files']['filelist'] = ret_2['filelist']
        return record


    def get_schema_config(self):
        pass

    def generate_query_doc_template(self) -> str:
        return util.load_config(self.__class__.config_path, 'query_template.py', load_json=False)

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

    def validate_query_result(self, result) -> bool:
        assert schemautil.validate(CortexExpSortedQueryResultSchemaJSL.get_schema(),
                                   {'cortex_exp_ref': str(result['_id']),
                                    'files_to_sort': result['recorded_files']})
        return True

    def prepare_post(self, query_result) -> dict:
        return {'result_ids': [ObjectId()],
                'files_to_sort': query_result['recorded_files'],
                'cortex_exp_ref': str(query_result['_id'])}
