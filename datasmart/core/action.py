import os
import pickle
from abc import abstractmethod
import json
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
        pass

    @abstractmethod
    def perform(self) -> None:
        """ the main method actually doing things.

        :return:
        """
        pass

    @abstractmethod
    def is_prepared(self) -> bool:
        pass

    @abstractmethod
    def is_finished(self) -> bool:
        pass

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

    @abstractmethod
    def __init__(self, config=None):
        super().__init__(config)
        prepare_path = self.get_prepare_path()
        self.__prepare_result_path = util.joinpath_norm(prepare_path, 'prepare_result.p')
        self.__query_template_path = util.joinpath_norm(prepare_path, 'query_template.py')
        self.__db_instance = DB()

        # you must define table_path as a class variable in the action.
        assert self.table_path is not DBAction.table_path
        assert isinstance(self.table_path, tuple)
        assert len(self.table_path) == 2 and isinstance(self.table_path[0], str) and isinstance(
            self.table_path[1], str)

        # initialize __prepare_result, __result_ids, if it's already prepared
        self.__prepare_result = None
        self.__result_ids = None
        self.is_prepared()

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

    def insert_results(self, results):
        assert isinstance(results, list)
        self.__db_instance.connect()
        collection_instance = self.__db_instance.client_instance[self.table_path[0]][self.table_path[1]]
        for result in results:
            assert result['_id'] in self.result_ids
            # assert isinstance(id, ObjectId)  # not necessarily true.
            assert (collection_instance.find_one({"_id": result['_id']}) is None)
            assert collection_instance.insert_one(result).acknowledged
        self.__db_instance.disconnect()

    def push_files(self, id_: ObjectId, filelist: list, site: dict = None, relative: bool = True, subdirs: list = None):
        filetransfer_instance = FileTransfer()
        self.__db_instance.connect()
        collection_instance = self.__db_instance.client_instance[self.table_path[0]][self.table_path[1]]
        # make sure we don't push files after record is constructed.
        assert collection_instance.find_one({"_id": id_}) is None, "only push files before inserting the record!"
        for x in filelist:
            assert (not os.path.isabs(x))
        # push file under {prefix}/self.table_path[0]/self.table_path[1]/id_.
        filetransfer_instance.push(filelist=filelist, site=site, relative=relative,
                                   subdirs=subdirs, dest_append_prefix=list(self.table_path+(str(id_),)))
        self.__db_instance.disconnect()

    def clear_results(self):
        """ delete result ids from the database, in case you want to start over.

        :return:
        """
        assert isinstance(self.result_ids, list)
        self.__db_instance.connect()
        collection_instance = self.__db_instance.client_instance[self.table_path[0]][self.table_path[1]]
        for id_ in self.result_ids:
            # assert isinstance(id, ObjectId)  # not necessarily true.
            collection_instance.delete_one({"_id": id_})
            assert collection_instance.find_one({"_id": id_}) is None
        self.__db_instance.disconnect()

    def is_inserted_one(self, id_):
        self.__db_instance.connect()
        collection_instance = self.__db_instance.client_instance[self.table_path[0]][self.table_path[1]]
        if collection_instance.find_one({"_id": id_}) is None:
            return False
        self.__db_instance.disconnect()

    def is_finished(self) -> bool:
        """ simply check that each result id is in the table
        :return:
        """
        if self.result_ids is None:
            return False

        assert isinstance(self.result_ids, list)
        try:
            self.__db_instance.connect()
            collection_instance = self.__db_instance.client_instance[self.table_path[0]][self.table_path[1]]
            for id_ in self.result_ids:
                # assert isinstance(id, ObjectId)  # not necessarily true.
                if collection_instance.find_one({"_id": id_}) is None:
                    return False
        finally:
            self.__db_instance.disconnect()

        return True

    def is_prepared(self) -> bool:
        """ check if the result is already there, and if there is, then put it in self._query_result and return True
        otherwise False.

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
        # run the query, passing it the database handle as 'client_instance'.
        locals_query = {'client_instance': self.__db_instance.client_instance}
        globals_query = {}
        with open(self.__query_template_path, 'rt') as f:
            exec(f.read(), globals_query, locals_query)
        self.__db_instance.disconnect()
        assert 'result' in locals_query, "I need a variable called 'result' after executing the query document!"

        # then based on this result, I need to generate a set of ids that will be inserted.
        assert self.validate_query_result(locals_query['result']), "the query result doesn't look good!"
        post_prepare_result = self.prepare_post(locals_query['result'])
        assert 'result_ids' in post_prepare_result
        assert post_prepare_result['result_ids'] is not None

        # check that results are not found.
        assert isinstance(post_prepare_result['result_ids'], list)
        self.__db_instance.connect()
        collection_instance = self.__db_instance.client_instance[self.table_path[0]][self.table_path[1]]
        for id_ in post_prepare_result['result_ids']:
            assert collection_instance.find_one({"_id": id_}) is None
        self.__db_instance.disconnect()

        self.__result_ids = post_prepare_result['result_ids']
        self.__prepare_result = post_prepare_result

        pickle.dump(post_prepare_result, open(self.__prepare_result_path, 'wb'))

    @abstractmethod
    def prepare_post(self, query_result) -> dict:
        """ generate a list of unique ids that will be inserted into the DB

        :param query_result:
        :return:
        """
        assert query_result is not None, "query result should not be None!"
        return {'result_ids': []}

    @abstractmethod
    def generate_query_doc_template(self) -> str:
        """ default template.
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
        self._dbschema_instance = self.__class__.dbschema(self.get_schema_config())

    @property
    def dbschema_instance(self):
        return self._dbschema_instance


class ManualDBActionWithSchema(DBActionWithSchema):
    def validate_query_result(self, result) -> bool:
        return super().validate_query_result(result)

    def generate_query_doc_template(self) -> str:
        return "result = {}"

    def prepare_post(self, query_result) -> dict:
        # ignore the query result, simply return a ID to go.
        return {'result_ids': [ObjectId()]}

    def perform(self) -> None:
        """ this is the main function actually doing things.
        :return:
        """
        self.export_record_template()
        input("Press Enter to continue after finish editing and saving the tempalte...")
        record = self.import_record_template()
        self.insert_results([record])
        print("done!")

    def export_record_template(self):
        savepath = util.joinpath_norm(self.global_config['project_root'],self.config['savepath'])
        if os.path.exists(savepath):
            print("file exists! I don't want to overwrite it, and I assume that file is your template.")
        else:
            with open(savepath, 'wt') as f:
                f.write(self.dbschema_instance.get_template())
        print('template document created at {}'.format(savepath))

    def import_record_template(self):
        with open(self.config['savepath'], 'rt') as f:
            record = self.dbschema_instance.generate_record(json.loads(f.read()))
        assert len(self.result_ids) == 1
        assert '_id' not in record
        # insert id_
        record['_id'] = self.result_ids[0]
        return record
