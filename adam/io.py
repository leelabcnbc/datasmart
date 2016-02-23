from os import path
from . import CortexExpSchema
from pymongo import MongoClient


def export_template(config):
    schema_name = config['schema_name']
    savepath = config['savepath']
    schema_instance = schema_mapping[schema_name](config)
    if path.exists(savepath):
        print("file exists! I don't want to overwrite it, and I assume that file is your template.")
    else:
        with open(savepath, 'w') as f:
            f.write(schema_instance.get_template())
    print('template document for schema {0} created at {1}'.format(
        schema_name, savepath
    ))
    return schema_instance


def import_template(schema_instance, config):
    with open(config['savepath'], 'r') as f:
        record = schema_instance.generate_record(f.read())
    return record


def insert_record(schema_instance, record, config):
    # connect to DB
    db_config = config['db']
    print('connect to DB {0} at port {1}'.format(db_config['url'], db_config['port']))
    client = MongoClient(db_config['url'], db_config['port'])
    if db_config['authentication']:
        client['admin'].authenticate(name=db_config['user'], password=db_config['password'])
    # get the particular collection.
    db, collection = schema_instance.where_to_insert()
    collection_instance = client[db][collection]
    # insert result.
    insert_result = collection_instance.insert_one(record)
    assert insert_result.acknowledged
    print('write successful with id {}'.format(insert_result.inserted_id))


schema_mapping = {
    'CortexExp': CortexExpSchema.CortexExpSchema
}
