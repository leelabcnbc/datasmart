from adam.core import util
from .RecordSchema import RecordSchema

"""
repo_hash now must be a github SHA1, so 40 digits.
"""


class CortexExpSchema(RecordSchema):
    def __init__(self, config=None):
        super(CortexExpSchema, self).__init__()
        if config is not None:
            assert 'cortex_expt_repo_url' in config
            assert 'cortex_expt_repo_hash' in config
            self.config = {
                'repo_url': config['cortex_expt_repo_url'],
                'repo_hash': config['cortex_expt_repo_hash']
            }
        else:
            self.config = {
                'repo_url': "https://github.com/leelabcnbc/lab-data-management",
                'repo_hash': "0000000000000000000000000000000000000000"
            }

    def post_process_record(self, record=None):
        """
        :param record: a Python dictionary representing the document to insert.
        :return: a dict ready to be inserted.
        """
        record['timestamp'] = util.rfc3339_to_datetime(record['timestamp'])
        return record

    def where_to_insert(self):
        """
        :return: the (db, collection) pair into which the document should be inserted.
        """
        return 'leelab_primate', 'cortex'

    def get_template_inner(self):
        processed_template = self.template_base.format(
            **{
                "timestamp": util.current_timestamp(),
                "monkeyname": "randommonkey",
                "experiment_name": "demo_experiment",
                "repo_url": self.config['repo_url'],
                "repo_hash": self.config['repo_hash']
            }
        )
        return processed_template

    def schema_doc(self):
        schema_doc = \
            """
            {
                "title": "Schema for a CORTEX experiment",
                "type": "object",
                "properties": {
                    "timestamp": {
                        "type": "string",
                        "format": "date-time"
                    },
                    "monkey": {
                        "type": "string"
                    },
                    "code_repo": {
                        "type": "object",
                        "properties": {
                            "repo_url": {
                                "type": "string",
                                "format": "uri"
                            },
                            "repo_hash": {
                                "type": "string",
                                "pattern": "^[0-9a-fA-F]{40}$"
                            }
                        },
                        "required": ["repo_url", "repo_hash"]
                    },
                    "experiment_name": {
                        "type": "string"
                    },
                    "recorded_files": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        },
                        "minItems": 1,
                        "uniqueItems": true
                    },
                    "additional_parameters": {
                        "type": "string"
                    },
                    "notes": {
                        "type": "string"
                    }
                },
                "required": ["timestamp", "monkey",
                "experiment_name", "code_repo",
                "recorded_files", "additional_parameters", "notes"]
            }
            """
        return schema_doc

    template_base = """
        {{
            "timestamp": "{timestamp}",
            "monkey": "{monkeyname}",
            "code_repo": {{
                "repo_url": "{repo_url}",
                "repo_hash": "{repo_hash}"
            }},
            "experiment_name": "{experiment_name}",
            "recorded_files": [
                "/leelab/data/xxx.NEV"
            ],
            "additional_parameters": "RF location: X: xx, Y: xx",
            "notes": ""
        }}
        """
