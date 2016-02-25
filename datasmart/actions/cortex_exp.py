from datasmart.core.dbschema import DBSchema
from datasmart.core import util
from datasmart.core.action import ManualDBActionWithSchema
import subprocess


class CortexExpSchema(DBSchema):
    schema_path = ('actions', 'cortex_exp')

    def __init__(self, config=None):
        super().__init__(config)

    def post_process_record(self, record=None):
        record['timestamp'] = util.rfc3339_to_datetime(record['timestamp'])
        return record

    def post_process_template(self, template: str):
        template = template.replace("{{timestamp}}", util.current_timestamp())
        template = template.replace("{{repo_url}}", self.config['repo_url'])
        template = template.replace("{{repo_hash}}", self.config['repo_hash'])
        return template


class CortexExpAction(ManualDBActionWithSchema):
    table_path = ('leelab_primate', 'cortex')
    config_path = ('actions', 'cortex_exp')
    dbschema = CortexExpSchema

    def __init__(self, config=None):
        super().__init__(config)

    @staticmethod
    def normalize_config(config: dict) -> dict:
        cortex_expt_repo_url = subprocess.check_output(['git', 'ls-remote', '--get-url', 'origin'],
                                                       cwd=config['cortex_expt_repo_path']).decode().strip()
        cortex_expt_repo_hash = subprocess.check_output(['git', 'rev-parse', '--verify', 'HEAD'],
                                                        cwd=config['cortex_expt_repo_path']).decode().strip()
        return {
            'cortex_expt_repo_url': cortex_expt_repo_url,
            'cortex_expt_repo_hash': cortex_expt_repo_hash,
            'savepath': config['savepath']
        }

    def get_schema_config(self):
        return {'repo_url': self.config['cortex_expt_repo_url'],
                'repo_hash': self.config['cortex_expt_repo_hash']}
