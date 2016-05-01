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
import shutil
import os.path
import stat

sort_methods = ['sacbatch_and_spikesort']
sort_people = ["Ge Huang"]


class CortexExpSortedQueryResultSchemaJSL(jsl.Document):
    cortex_exp_ref = jsl.StringField(pattern=schemautil.StringPatterns.bsonObjectIdPattern, required=True)
    files_to_sort = jsl.DocumentField(schemautil.filetransfer.FileTransferSiteAndFileListRemote, required=True)


class CortexExpSortedSchemaJSL(jsl.Document):
    schema_revision = jsl.IntField(enum=[1], required=True)  # the version of schema, in case we have drastic change
    cortex_exp_ref = jsl.StringField(format=schemautil.StringPatterns.bsonObjectIdPattern, required=True)
    files_to_sort = jsl.DocumentField(schemautil.filetransfer.FileTransferSiteAndFileListRemote, required=True)
    sorted_files = jsl.DocumentField(schemautil.filetransfer.FileTransferSiteAndFileListRemoteAuto, required=True)
    sort_method = jsl.StringField(enum=sort_methods, required=True)
    sort_config = jsl.DictField(required=True)  # arbitrary dict to save the parameters for this sort.
    sort_person = jsl.StringField(enum=sort_people, required=True)  # who sorted.
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
        record['cortex_exp_ref'] = ObjectId(record['cortex_exp_ref'])
        return record

    def post_process_template(self, template: str) -> str:
        return template


class CortexExpSortedAction(DBActionWithSchema):
    def perform(self) -> None:
        for idx, method in enumerate(sort_methods, start=1):
            print("{}: {}".format(idx, method))
        sort_choice_idx = int(
            input("{} Step 1a please choose the method to do sorting, from {} to {}:  ".format(self.class_identifier,
                                                                                               1, len(sort_methods))))
        assert 1 <= sort_choice_idx <= len(sort_methods), "invalid method!"
        sort_choice = sort_methods[sort_choice_idx - 1]
        input("{} Step 1b press enter to start using method {}".format(self.class_identifier, sort_choice))
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
            ('schema_revision', 1),
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
                                    "{} Step 2.1 please edit files to sort in 'files_to_sort', "
                                    "and edit notes and sort person (even add more files to sort). don't "
                                    "care about sorted_files now...".format(self.class_identifier),
                                    overwrite=False, load_json=True)
        # first, keep only NEV files
        assert self.dbschema_instance.validate_record(record)
        for file in record['files_to_sort']['filelist']:
            assert file.lower().endswith('.nev'), "only NEV files are supported!"

        print("now {} NEV files will be downloaded to {}".format(
            len(record['files_to_sort']['filelist']),
            self.get_file_transfer_config()['local_data_dir']
        ))
        input("{} Step 2.2 press enter to continue".format(self.class_identifier))
        ret = self.fetch_files(record['files_to_sort']['filelist'], record['files_to_sort']['site'],
                               relative=False, local_fetch_option='copy')
        filelist_local = ret['filelist']
        local_dir = ret['dest']['path']
        for file in filelist_local:
            assert os.path.basename(file) == file

        filelist_cell = ["'" + file + "'" for file in filelist_local]
        filelist_cell = "{" + ",".join(filelist_cell) + "}"
        print(filelist_cell)
        input('{} Step 2.3 the above files will be put into sorting. press enter to continue'.format(
            self.class_identifier))

        sacbatch_script = util.load_config(self.__class__.config_path, 'sacbatch_script.m', load_json=False)
        spikesort_script = util.load_config(self.__class__.config_path, 'spikesort_script.m', load_json=False)

        sacbatch_script = sacbatch_script.format(filelist_cell)
        spikesort_script = spikesort_script.format(filelist_cell)

        main_script = util.load_config(self.__class__.config_path, 'sacbatch_and_spikesort_script.sh', load_json=False)

        with open(os.path.join(local_dir, 'sacbatch_script.m'), 'wt', encoding='utf-8') as f:
            f.write(sacbatch_script)
        with open(os.path.join(local_dir, 'spikesort_script.m'), 'wt', encoding='utf-8') as f:
            f.write(spikesort_script)

        main_script_local = os.path.join(local_dir, 'sacbatch_and_spikesort_script.sh')
        with open(main_script_local, 'wt', encoding='utf-8') as f:
            f.write(main_script)
        # add executable bit to the file.
        os.chmod(main_script_local, stat.S_IEXEC | os.stat(main_script_local).st_mode)

        # copy files
        sacbatch_file = util.joinpath_norm('SAC_batch_summer.tar.gz')
        spikesort_file = util.joinpath_norm('spikesort.tar.gz')

        shutil.copyfile(os.path.join(self.config['spike_sorting_software_repo_path'], sacbatch_file),
                        os.path.join(local_dir, 'SAC_batch.tar.gz'))
        shutil.copyfile(os.path.join(self.config['spike_sorting_software_repo_path'], spikesort_file),
                        os.path.join(local_dir, 'spikesort.tar.gz'))

        system_info_file = os.path.join(local_dir, 'system_info')
        sacbatch_output_file = os.path.join(local_dir, 'sacbatch_output')
        open(system_info_file, 'wb').close()
        open(sacbatch_output_file, 'wb').close()
        # add all permissions.
        os.chmod(system_info_file, 0o777)
        os.chmod(sacbatch_output_file, 0o777)
        # now time to write a script for sac batch.
        prompt_text = "{} Step 2.4 SAC script {} and SpikeSort script {} are in {}, run them outside and then press enter".format(
            self.class_identifier, "sacbatch_script.m", "spikesort_script.m",
            self.get_file_transfer_config()['local_data_dir']
        )

        input(prompt_text)
        input("{} Step 2.5 press again if you are really sure you are finished.".format(self.class_identifier))

        # then collect info
        with open(os.path.join(local_dir, 'system_info'), 'rt', encoding='utf-8') as f:
            system_info = f.read()
        with open(os.path.join(local_dir, 'sacbatch_output'), 'rt', encoding='utf-8') as f:
            sacbatch_output = f.read()
        record['sort_config']['system_info'] = system_info
        record['sort_config']['sacbatch_output'] = sacbatch_output
        record['sort_config']['action_config'] = self.config
        record['sort_config']['sacbatch_file'] = sacbatch_file
        record['sort_config']['spikesort_file'] = spikesort_file
        record['sort_config']['sacbatch_script'] = sacbatch_script
        record['sort_config']['spikesort_script'] = spikesort_script
        record['sort_config']['master_script'] = main_script
        print("now dry run file upload to get the locations of loaded file")
        ret_2 = self.push_files(insert_id, filelist_local, relative=False, dryrun=True)
        record['sorted_files']['site'] = ret_2['dest']
        record['sorted_files']['filelist'] = ret_2['filelist']
        record_old = record
        record = save_wait_and_load(json.dumps(record, indent=2),
                                    self.config['savepath'],
                                    "{} Step 2.6 you can remove some files to upload at this step, "
                                    "if you added some files before to sort files of the same day together".format(
                                        self.class_identifier), overwrite=True, load_json=True)
        # first, keep only NEV files
        assert self.dbschema_instance.validate_record(record)
        filelist_local_new = [os.path.basename(f) for f in record['sorted_files']['filelist']]
        assert set(record['sorted_files']['filelist']) <= set(ret_2['filelist']), "you can only remove files!"
        assert set(filelist_local_new) <= set(filelist_local), "you can only remove files!"
        del record_old['sorted_files']['filelist']
        del record['sorted_files']['filelist']
        assert record_old == record, "don't change anything other than file list!"
        print("now {} sorted NEV files will be uploaded".format(len(filelist_local_new)))
        ret_2 = self.push_files(insert_id, filelist_local_new, relative=False)

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
        return [record['sorted_files']['site']]

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

    @staticmethod
    def normalize_config(config: dict) -> dict:
        spike_sorting_software_repo_path = config['spike_sorting_software_repo_path']
        spike_sorting_software_repo_url = util.get_git_repo_url(spike_sorting_software_repo_path)
        spike_sorting_software_repo_hash = util.get_git_repo_hash(spike_sorting_software_repo_path)
        util.check_git_repo_clean(spike_sorting_software_repo_path)
        return {
            'spike_sorting_software_repo_url': spike_sorting_software_repo_url,
            'spike_sorting_software_repo_hash': spike_sorting_software_repo_hash,
            'spike_sorting_software_repo_path': spike_sorting_software_repo_path,
            'savepath': config['savepath']
        }
