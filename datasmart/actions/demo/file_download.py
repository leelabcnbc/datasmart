import datasmart.core.util.config
import datasmart.core.util.path
from datasmart.core import schemautil
from datasmart.core.action import DBAction
from datasmart.core.util import util_old


class FileDownloadAction(DBAction):
    db_modification = False
    config_path = ('actions', 'demo', 'file_download')

    def __init__(self, config=None):
        super().__init__(config)

    def generate_query_doc_template(self) -> str:
        return datasmart.core.util.config.load_config(self.__class__.config_path, 'query_template.py', load_json=False)

    def validate_query_result(self, result) -> bool:
        # must be a good site + file list.
        assert schemautil.validate(schemautil.filetransfer.FileTransferSiteAndFileListAny.get_schema(),result)
        return True

    def perform(self) -> None:
        site = self.prepare_result['site']
        filelist = self.prepare_result['filelist']
        print("prepare to download {} files from site {}...".format(len(filelist), str(site)))
        print("downloaded files will be under {} of {}".format(
            datasmart.core.util.path.joinpath_norm(*(self.config['savedir'])),
            self.get_file_transfer_config()['local_data_dir']))
        response = input("are you sure? Enter to move forward, enter anything then enter to stop")
        if response:
            print("operation stopped!")
            return
        self.fetch_files(filelist, site, relative=True, subdirs=self.config['savedir'],local_fetch_option='copy')
        print("succeed!")
        self.force_finished = True

    def prepare_post(self, query_result) -> dict:
        return {'result_ids': [], 'site': query_result['site'], 'filelist': query_result['filelist']}

    # only for overriding...
    def is_stale(self, record, db_instance) -> bool:
        pass

    def remove_files_for_one_record(self, record):
        pass