"""DataSMART action for uploading metadata about a CORTEX experiment.
Format of a database record for this action.

.. literalinclude:: /../datasmart/config/actions/leelab/cortex_exp/template.json
   :language: json

* ``schema_revision`` the major revision number for schema.
* ``timestamp`` this field will be replaced with the time this template is generated during execution.
* ``monkey`` the monkey performing this experiment. Now can be one of ``["leo", "koko", "gabby", "frugo"]`` (see code)
* ``code_repo`` this field will be replaced with the remote url of repository and the current commit.
* ``experiment_name`` name of experiment. this should map to a (sub) directory of the repository.
  Say ``test1`` or ``test1/subtest``.
* ``timing_file_name``, ``condition_file_name``, ``item_file_name`` names of ``tm``, ``cnd``, and ``itm`` files used.
  Must be all lowercase. In addition, ``timing_file_sha1``, ``condition_file_sha1``, ``item_file_sha1`` will be inserted
  into the database as well in the end.
* ``condition_stimulus_mapping``: an array whose each element is a dictionary having
  ``condition_number`` and the stimuli actually associated with this condition. Here only an example is shown.
  ``ctx`` file names must be all lowercase.
* ``recorded_files``: the files uploaded for this experiment. DataSMART will check that these files indeed exist before
  inserting the database record.
* ``additional_parameters`` some other parameters. maybe experimenters can fill this field with some specified format,
  in case computer parsing of this field is required.
* ``notes`` free form notes on this experiment.

"""

from datasmart.core.dbschema import DBSchema
from datasmart.core import util
from datasmart.core.action import ManualDBActionWithSchema
import jsl
from datasmart.core import schemautil
import os.path
import hashlib
import re
monkeylist = ["leo", "koko", "gabby", "frugo"]


class CortexExpSchemaJSL(jsl.Document):
    """class defining json schema for a database record. See top of file"""
    schema_revision = jsl.IntField(enum=[1], required=True)  # the version of schema, in case we have drastic change
    timestamp = jsl.StringField(format="date-time", required=True)
    monkey = jsl.StringField(enum=monkeylist, required=True)
    code_repo = jsl.DocumentField(schemautil.GitRepoRef, required=True)
    experiment_name = jsl.StringField(required=True, pattern=schemautil.StringPatterns.relativePathPattern)
    timing_file_name = jsl.StringField(pattern=schemautil.StringPatterns.strictFilenameLowerPattern('tm'),
                                       required=True)
    condition_file_name = jsl.StringField(pattern=schemautil.StringPatterns.strictFilenameLowerPattern('cnd'),
                                          required=True)
    item_file_name = jsl.StringField(pattern=schemautil.StringPatterns.strictFilenameLowerPattern('itm'),
                                     required=True)
    parameter_file_name = jsl.StringField(pattern=schemautil.StringPatterns.strictFilenameLowerPattern('par'),
                                          required=True)
    recorded_files = jsl.DocumentField(schemautil.filetransfer.FileTransferSiteAndFileListRemote, required=True)
    additional_parameters = jsl.DictField(required=True)
    notes = jsl.StringField(required=True)


class CortexExpSchema(DBSchema):
    schema_path = ('actions', 'leelab', 'cortex_exp')

    def get_schema(self) -> dict:
        return CortexExpSchemaJSL.get_schema()

    def __init__(self, config=None):
        super().__init__(config)

    def post_process_record(self, record=None) -> dict:
        """ add file hash, check file exists.

        :param record: the record input by the user and validated against the schema.
        :return: the final record to be inserted.
        """

        # check git clean. I put it here for some mock related issues. Somehow putting git_hash under
        # CortexExpSchema doesn't work.
        # check
        cortex_expt_repo_hash = util.get_git_repo_hash(self.config['repo_path'])
        assert cortex_expt_repo_hash == record['code_repo']['repo_hash'], \
            'you may updated the repo after creating the template!'
        util.check_git_repo_clean(self.config['repo_path'])

        # convert string-based timestamp to actual Python ``datetime`` object
        record['timestamp'] = util.rfc3339_to_datetime(record['timestamp'])
        # check the item files, condition files, and timing files.
        file_to_check_list = [record['timing_file_name'],
                              record['condition_file_name'],
                              record['item_file_name'],
                              record['parameter_file_name']]
        field_to_insert_list = ['timing_file_sha1',
                                'condition_file_sha1',
                                'item_file_sha1',
                                'parameter_file_sha1']
        for file_to_check, field_to_insert in zip(file_to_check_list, field_to_insert_list):
            file_to_check_full = os.path.join(self.config['repo_path'], record['experiment_name'], file_to_check)
            assert os.path.exists(file_to_check_full), "file {} doesn't exist!".format(file_to_check_full)
            # load the file
            with open(file_to_check_full, 'rb') as f:
                sha1_this = hashlib.sha1(f.read()).hexdigest()
            assert re.fullmatch(schemautil.StringPatterns.sha1Pattern, sha1_this)
            assert field_to_insert not in record
            record[field_to_insert] = sha1_this

        return record

    def post_process_template(self, template: str) -> str:
        template = template.replace("{{timestamp}}", util.current_timestamp())
        template = template.replace("{{repo_url}}", self.config['repo_url'])
        template = template.replace("{{repo_hash}}", self.config['repo_hash'])
        return template


class CortexExpAction(ManualDBActionWithSchema):
    def sites_to_remove(self, record):
        return []

    def custom_info(self) -> str:
        return "this is the DataSMART action for saving metadata for a CORTEX experiment.\n" \
               "Please modify {} to your need".format(self.config['savepath'])

    def before_insert_record(self, record):
        print("check that files are really there...")
        site = record['recorded_files']['site']
        filelist = record['recorded_files']['filelist']
        ret = self.check_file_exists(site, filelist, unique=True)
        record['recorded_files']['site'] = ret['src']
        record['recorded_files']['filelist'] = ret['filelist']

    table_path = ('leelab', 'cortex_exp')
    config_path = ('actions', 'leelab', 'cortex_exp')
    dbschema = CortexExpSchema

    def __init__(self, config=None):
        super().__init__(config)

    @staticmethod
    def normalize_config(config: dict) -> dict:
        cortex_expt_repo_url = util.get_git_repo_url(config['cortex_expt_repo_path'])
        cortex_expt_repo_hash = util.get_git_repo_hash(config['cortex_expt_repo_path'])
        util.check_git_repo_clean(config['cortex_expt_repo_path'])
        return {
            'cortex_expt_repo_url': cortex_expt_repo_url,
            'cortex_expt_repo_hash': cortex_expt_repo_hash,
            'cortex_expt_repo_path': config['cortex_expt_repo_path'],
            'savepath': config['savepath']
        }

    def get_schema_config(self):
        return {'repo_url': self.config['cortex_expt_repo_url'],
                'repo_hash': self.config['cortex_expt_repo_hash'],
                'repo_path': self.config['cortex_expt_repo_path']}
