import json
import os
import pickle
from abc import abstractmethod

from bson import ObjectId

from . import util
from .base import Base
from .db import DB
from .dbschema import DBSchema
from .filetransfer import FileTransfer


class Action(Base):
    @abstractmethod
    def __init__(self, config=None):
        super().__init__(config)

    @abstractmethod
    def prepare(self) -> None:
        """ the first phase of an action.

        :return: None should make sure it runs without throw exception if and only if is_prepared returns True.
        """
        pass

    @abstractmethod
    def perform(self) -> None:
        """ the second phase of an action.
        the main method actually doing things.

        :return: None. should make sure it runs without throw exception if and only if is_finished returns True.
        """
        pass

    @abstractmethod
    def is_prepared(self) -> bool:
        """ check if first phase is done.

        :return:
        """
        pass

    @abstractmethod
    def is_finished(self) -> bool:
        """ check if second phase is done.

        :return:
        """
        pass

    def revoke(self):
        """ negate the effects of this action.

        :return:
        """
        raise RuntimeError("this action can't be revoked!")

    def run(self):
        if self.is_finished():
            print("the action has been finished!")
        else:
            if not self.is_prepared():
                self.prepare()
            assert self.is_prepared(), "the action has not been prepared!"
            self.perform()
            assert self.is_finished(), "the action has been performed, but not considered finished!"


class DBAction(Action):
    table_path = (None, None)
    db_modification = True  # whether this action would change the DB.

    @abstractmethod
    def __init__(self, config=None):
        super().__init__(config)
        prepare_path = self.get_prepare_path()
        self.__prepare_result_path = util.joinpath_norm(prepare_path, 'prepare_result.p')
        self.__query_template_path = util.joinpath_norm(prepare_path, 'query_template.py')
        self.__db_instance = DB()

        # you must define table_path as a class variable in the action.
        if self.__class__.db_modification:
            assert self.table_path is not DBAction.table_path
            assert isinstance(self.table_path, tuple)
            assert len(self.table_path) == 2 and isinstance(self.table_path[0], str) and isinstance(
                self.table_path[1], str)
        else:
            assert self.table_path is DBAction.table_path, "you don't modify table_path for non-modifying action"

        # initialize __prepare_result, __result_ids, if it's already prepared
        self.__prepare_result = None
        self.__result_ids = None
        self.force_finished = False  # useful for some Action without any __result_ids ([]) to make them finishable.
        self.is_prepared()

    @staticmethod
    def get_file_transfer_config():
        return FileTransfer().config

    def get_prepare_path(self):
        return self.global_config['project_root']

    @property
    def prepare_result(self):
        return self.__prepare_result

    @property
    def table_path(self) -> tuple:
        return self.__class__.table_path

    @property
    def result_ids(self):
        return self.__result_ids

    # def find_one_arbitrary(self, _id, table_path):
    #     """ check if a record exists in any arbitrary (db, collection).
    #
    #     base for constraints among collections.
    #     :return:
    #     """
    #     assert len(table_path) == 2
    #     self.__db_instance.connect()
    #     collection_instance = self.__db_instance.client_instance[table_path[0]][table_path[1]]
    #     result = collection_instance.find_one({"_id": _id})
    #     self.__db_instance.disconnect()
    #     return result

    def insert_results(self, results):
        assert isinstance(results, list)
        self.__db_instance.connect()
        try:
            collection_instance = self.__db_instance.client_instance[self.table_path[0]][self.table_path[1]]
            for result in results:
                assert result['_id'] in self.result_ids
                assert isinstance(result['_id'], ObjectId)  # must be true by design.
                assert (collection_instance.find_one({"_id": result['_id']}) is None)
                assert collection_instance.insert_one(result).acknowledged
        finally:
            self.__db_instance.disconnect()

    def push_files(self, _id: ObjectId, filelist: list, site: dict = None, relative: bool = True,
                   subdirs: list = None, dryrun: bool = False):
        assert _id in self.result_ids, "you can only push files related to you!"
        filetransfer_instance = FileTransfer()
        self.__db_instance.connect()
        try:
            collection_instance = self.__db_instance.client_instance[self.table_path[0]][self.table_path[1]]
            # make sure we don't push files after record is constructed.
            assert collection_instance.find_one({"_id": _id}) is None, "only push files before inserting the record!"
            for x in filelist:
                assert (not os.path.isabs(x))
            # push file under {prefix}/self.table_path[0]/self.table_path[1]/_id.
            # {prefix}/self.table_path[0]/self.table_path[1] must have been created beforehand, since rsync can only
            # create one level of folders.
            ret = filetransfer_instance.push(filelist=filelist, dest_site=site, relative=relative, subdirs=subdirs,
                                             dest_append_prefix=list(self.table_path + (str(_id),)),
                                             dryrun=dryrun)
        finally:
            self.__db_instance.disconnect()
        return ret

    @staticmethod
    def fetch_files(filelist: list, site: dict = None, relative: bool = True,
                    subdirs: list = None, local_fetch_option=None, dryrun: bool = False,
                    strip_append_prefix=True):  # remove strip prefix de

        if 'append_prefix' in site and strip_append_prefix:
            strip_prefix = site['append_prefix']
        else:
            strip_prefix = ''
        filetransfer_instance = FileTransfer()
        ret = filetransfer_instance.fetch(filelist=filelist, src_site=site, relative=relative, subdirs=subdirs,
                                          local_fetch_option=local_fetch_option, dryrun=dryrun,
                                          strip_prefix=strip_prefix)
        return ret

    @abstractmethod
    def is_stale(self, record, db_instance) -> bool:
        """check if one record is no longer needed.

        with db_instance, you can do all kinds of check. such as checking whether some of your
        references still exist in other parts of the DB.

        :return:
        """
        return True

    @abstractmethod
    def remove_files_for_one_record(self, record):
        """ this method defines how to remove files associated with a record, given the record itself.

        :param record: the record whose associated files is to be removed.
        :return: None if everything works fine. Otherwise, throw some exception.
        """
        assert self.remove_files_for_one_record is not DBAction.remove_files_for_one_record, "you must override del!"
        # I think the easist way is calling remove_files over all sites.

    def remove_one_record(self, collection_instance, record):
        """  internal method to completely remove a record.

        :param collection_instance:
        :param record:
        :return:
        """
        assert collection_instance.find_one({"_id": record['_id']}) is not None
        self.remove_files_for_one_record(record)
        collection_instance.delete_one({"_id": record['_id']})
        assert collection_instance.find_one({"_id": record['_id']}) is None

    def remove_files(self, _id, site_list) -> None:
        """ remove the files associated with one ``_id`` in this collection, over many sites.

        By design, I assumed that you upload your files in the form of
        ``prefix/table_path[0]/table_path[1]/str(_id)``.

        if prefix is not supplied, then I assume that you want to delete these files with the standard prefix
        defined in db.config.

        So I will simply check

        :param _id: _id field of the record.
        :param site_list: which site's file to remove?
        :return: None if everything is fine; otherwise throws errors.
        """

        # first send ssh command to rm dir, and then get back the return value. make sure succeed.
        # then remove the record id.
        if len(site_list) == 0:
            return
        filetransfer = FileTransfer()
        correct_append_prefix = util.joinpath_norm(*(self.table_path + (str(_id),)))
        for site in site_list:
            assert site['append_prefix'] == correct_append_prefix
            filetransfer.remove_dir(site)

    def global_clean_up(self):
        """
        :return:
        """

        # first find all documents.
        # then for loop
        # then check if is stale
        # then remove it if stale.
        self.__db_instance.connect()
        try:
            collection_instance = self.__db_instance.client_instance[self.table_path[0]][self.table_path[1]]
            for record in collection_instance.find():
                if self.is_stale(record, self.__db_instance):
                    print("the following record will be cleaned up:")
                    print(record)
                    input("press enter to confirm... otherwise, press ctrl+c to stop")
                    self.remove_one_record(collection_instance, record)
        finally:
            self.__db_instance.disconnect()

    def revoke(self):
        """ delete result ids from the database, in case you want to start over.
        TODO: rewrite using remove_one_result
        :return:
        """
        assert isinstance(self.result_ids, list)
        self.__db_instance.connect()
        try:
            collection_instance = self.__db_instance.client_instance[self.table_path[0]][self.table_path[1]]
            for _id in self.result_ids:
                record = collection_instance.find_one({"_id": _id})
                if record is not None:
                    self.remove_one_record(collection_instance, record)
        finally:
            self.__db_instance.disconnect()
        print("done clearing!")

    def is_inserted_one(self, _id):
        """ this can be used to help a partially executed operation to identify which results need insertion.

        :param _id:
        :return:
        """
        self.__db_instance.connect()
        try:
            collection_instance = self.__db_instance.client_instance[self.table_path[0]][self.table_path[1]]
            if collection_instance.find_one({"_id": _id}) is None:
                return False
        finally:
            self.__db_instance.disconnect()
        return True

    def is_finished(self) -> bool:
        """ simply check that each result id is in the table
        :return:
        """
        if self.force_finished:
            return True

        if self.result_ids is None:
            return False

        assert isinstance(self.result_ids, list)

        if not self.result_ids:  # empty list, always false, use force_finished to escape.
            return False

        try:
            self.__db_instance.connect()
            collection_instance = self.__db_instance.client_instance[self.table_path[0]][self.table_path[1]]
            for _id in self.result_ids:
                assert isinstance(_id, ObjectId)
                if collection_instance.find_one({"_id": _id}) is None:
                    return False
        finally:
            self.__db_instance.disconnect()

        return True

    def is_prepared(self) -> bool:
        """ check if the result is already there, and if there is, then put it in self._query_result and return True
        otherwise False. if there are any exceptions, then certainly it also means bad.

        :return:
        """
        # either it's set or not set.
        assert ((self.prepare_result is not None) and (self.result_ids is not None)) or (
            (self.prepare_result is None) and (self.result_ids is None))

        if (self.prepare_result is not None) and (self.result_ids is not None):
            return True

        if os.path.exists(self.__prepare_result_path):
            prepare_result = pickle.load(open(self.__prepare_result_path, 'rb'))
            assert 'result_ids' in prepare_result, "the pickled result looked bad!"
            self.__prepare_result = prepare_result
            self.__result_ids = prepare_result['result_ids']
            return True

        return False

    def prepare(self):
        if not os.path.exists(self.__query_template_path):
            with open(self.__query_template_path, 'wt') as f:
                f.write(self.generate_query_doc_template())
            # TODO: add some non-interactive option to faciliate testing,
            # or use some tool to do it (probably 2nd is better for now)
            input("a query doc template is at {}, "
                  "please finish it and press Enter".format(self.__query_template_path))
        else:
            input("the query doc is already at {},"
                  "please confirm it and press Enter.".format(self.__query_template_path))

        assert os.path.exists(self.__query_template_path)
        self.__db_instance.connect()
        try:
            # run the query, passing it the database handle as 'client_instance'.
            locals_query = {'client_instance': self.__db_instance.client_instance}
            globals_query = {}
            with open(self.__query_template_path, 'rt') as f:
                exec(f.read(), globals_query, locals_query)
        finally:
            self.__db_instance.disconnect()
        assert 'result' in locals_query, "I need a variable called 'result' after executing the query document!"

        # then based on this result, I need to generate a set of ids that will be inserted.
        assert self.validate_query_result(locals_query['result']), "the query result doesn't look good!"
        post_prepare_result = self.prepare_post(locals_query['result'])
        assert 'result_ids' in post_prepare_result
        assert post_prepare_result['result_ids'] is not None

        # check that results are not found.
        assert isinstance(post_prepare_result['result_ids'], list)
        if post_prepare_result['result_ids']:
            self.__db_instance.connect()
            try:
                collection_instance = self.__db_instance.client_instance[self.table_path[0]][self.table_path[1]]
                for _id in post_prepare_result['result_ids']:
                    assert collection_instance.find_one(
                        {"_id": _id}) is None, "the proposed result ids exist in the DB!"
            finally:
                self.__db_instance.disconnect()

        self.__result_ids = post_prepare_result['result_ids']
        self.__prepare_result = post_prepare_result

        pickle.dump(post_prepare_result, open(self.__prepare_result_path, 'wb'))

    @abstractmethod
    def prepare_post(self, query_result) -> dict:
        """ minimally, generate a list of unique ids that will be inserted into the DB

        this step could involve other things, such as letting user input some action-specific data.
        :param query_result:
        :return:
        """
        assert query_result is not None, "query result should not be None!"
        return {'result_ids': []}

    @abstractmethod
    def generate_query_doc_template(self) -> str:
        """ default query document template.

        :return:
        """
        return "result = None"

    @abstractmethod
    def validate_query_result(self, result) -> bool:
        """ check that the query result can be used in the next step.

        :param result:
        :return: True by default.
        """
        assert result is not None, "query result should not be None!"
        return True

    @abstractmethod
    def perform(self) -> None:
        """ this is the main function actually doing things.
        :return:
        """
        pass


class DBActionWithSchema(DBAction):
    dbschema = DBSchema

    @abstractmethod
    def get_schema_config(self):
        return {}

    @abstractmethod
    def __init__(self, config=None):
        super().__init__(config)
        assert self.__class__.dbschema is not DBActionWithSchema.dbschema
        self.__dbschema_instance = self.__class__.dbschema(self.get_schema_config())

    @property
    def dbschema_instance(self):
        return self.__dbschema_instance

    def remove_files_for_one_record(self, record):
        self.remove_files(record['_id'], self.sites_to_remove(record))

    @abstractmethod
    def sites_to_remove(self, record):
        """ a list of sites to remove.
        I put this here because I assume your things have schema, so we don't need free form stuff to determine
        what to remove.
        :param record:
        :return:
        """
        pass


class ManualDBActionWithSchema(DBActionWithSchema):
    def is_stale(self, record, db_instance) -> bool:
        # manually typed stuff never goes stale...
        return False

    @abstractmethod
    def __init__(self, config=None):
        super().__init__(config)

    def validate_query_result(self, result) -> bool:
        return super().validate_query_result(result)

    def generate_query_doc_template(self) -> str:
        return "result = {}"

    def prepare_post(self, query_result) -> dict:
        # ignore the query result, simply return a ID to go.
        return {'result_ids': [ObjectId()]}

    @abstractmethod
    def before_insert_record(self, record):
        """ this can be used to upload files, etc.

        :param record:
        :return: None if nothing happens. throw exception if bad thing happens.
        """
        pass

    @abstractmethod
    def custom_info(self) -> str:
        return ""

    def perform(self) -> None:
        """ this is the main function actually doing things.

        :return:
        """
        self.export_record_template()
        print("custom info from this action follows.")
        print(self.custom_info())
        input("Press Enter to continue after finish editing and saving the tempalte...")
        record = self.import_record_template()
        self.before_insert_record(record)
        self.insert_results([record])
        print("done!")

    def export_record_template(self):
        savepath = util.joinpath_norm(self.global_config['project_root'], self.config['savepath'])

        if os.path.exists(savepath):
            print("file exists! I don't want to overwrite it, and I assume that file is your template.")
        else:
            template_text = self.dbschema_instance.get_template()
            with open(savepath, 'wt') as f:
                f.write(template_text)
        print('template document created at {}'.format(savepath))

    def import_record_template(self):
        with open(self.config['savepath'], 'rt') as f:
            record = self.dbschema_instance.generate_record(json.loads(f.read()))
        assert len(self.result_ids) == 1
        assert '_id' not in record
        # insert _id
        record['_id'] = self.result_ids[0]
        return record
