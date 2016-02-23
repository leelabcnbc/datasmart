from . import io


def main(config):
    """
    main program for uploading a experiment document to MongoDB.
    :param config: a dictionary containing all server info and where to save the template, and the schema.
    :return:
    """
    # get template written to disk.
    schema_instance = io.export_template(config)
    # wait for user to finish editing.
    input("Press Enter to continue after finish editing...")
    # get back the template.
    record = io.import_template(schema_instance, config)
    # connect the DB, and then insert the record.
    io.insert_record(schema_instance, record, config)
