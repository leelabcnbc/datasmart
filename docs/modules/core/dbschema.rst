*******************
``dbschema`` module
*******************

What is a schema
================

"schema" is a word of multiple meanings in the database world. Here, schema means a set of specification on how a row
in a database table should look like, as used in https://www.mongodb.com/presentations/schema-design-basics-1 .
In the world of relational database, we must specify a schema before inserting data into a table.
An example SQL table creation statement is as follows.

.. code-block:: sql

    CREATE TABLE Persons
    (
        PersonID int,
        LastName varchar(255),
        FirstName varchar(255),
        Address varchar(255),
        City varchar(255)
    );

In MongoDB, we don't need a schema for a table; a table can accept rows of any form. However, in order to facilitate
query, a schema is always needed.

Schema and NoSQL
----------------

As a NoSQL database, MongoDB doesn't require a schema. However, that doesn't mean we can abuse it. With free-form data
in the database, no useful query can be done. Instead, we should only consider this as a design flexibility. In case
you need to modify the schema a little, without tempering with all old records, you can simply insert the new-format
records right away, and deal with this structure difference in the application code.


Specifying a Schema in DataSMART
================================

As records in MongoDB in `BSON`_ format, which is an extension to `JSON`_, we use `JSON Schema`_ to define the schema.
It's much richer than only specifying data types. A JSON Schema is written in JSON and specifies how a JSON document
should look like. An example is given below, from http://json-schema.org/examples.html .

.. code-block:: json

    {
	  "title": "Example Schema",
	  "type": "object",
	  "properties": {
		"firstName": {
          "type": "string"
		},
		"lastName": {
          "type": "string"
		},
		"age": {
          "description": "Age in years",
          "type": "integer",
          "minimum": 0
		}
	  },
	  "required": ["firstName", "lastName"]
    }


This schema specifies that a JSON object conforming to this schema must be a
JSON object (in the context of `JSON`_ definition) with at least keys ``firstName`` and ``lastName``, whose values
are both strings, and an optional ``age`` key, whose value must be a non-negative integer.

Write schema using ``jsl``
--------------------------

While JSON schemas are JSON documents, it is tedious to write them by hand. Fortunately,
there is a great package `jsl`_ in Python to help us write schema in a less painful way.
It's easy to learn and it's the recommended way to write schema, for its clarity and ease of reuse.
All schemas in DataSMART are specified actually with ``jsl`` and then converted to JSON.


.. _dbschema-things-not-specifiable:

Things not specifiable via JSON Schema
--------------------------------------

Not every type of document validation can be done with JSON Schema. There are two reasons.

#. JSON has fewer types than BSON, which is used in MongoDB. Certain types in JSON, such as Binary data and Date
   (see `<https://docs.mongodb.org/manual/reference/bson-types/>`_),
   have no correspondence in JSON [#f1]_. For these types, there are two options.
    #. we can first ignore it, and insert the data later after an initial verification through JSON schema,
       and perform some custom validation later.
    #. for some particular types, such as Date, there's some thing very close in JSON Schema: the "format" attribute for
       a string type. For example, to ensure that users type in a valid time, we can specify a string field with
       "format" as "date-time", and we will later convert this string-based time into a Python ``datetime`` object.

#. Some validation logic is not expressible in JSON Schema. For example, for an object with three integer fields,
   we want to make sure the values of these three always sum to 10. This kind of complicated logic needs manual
   validation forever.


.. [#f1] This in theory can be solved using some MongoDB ORM-like layers, such as
         `MongoEngine <https://github.com/MongoEngine>`_, `Humongolus <https://github.com/entone/Humongolus>`_,
         `MongoKit <https://github.com/namlook/mongokit>`_. A full list can be seen at
         `Here <http://api.mongodb.org/python/current/tools.html>`_. These tools have validation tools on BSON.
         However, I feel the trouble they would bring outweighs the flexibility and simplicity of using raw MongoDB.
         Since JSON Schema can handle probably over 95% validation requirements, I think it's good enough.




``DBSchema`` class
==================

:class:`datasmart.core.dbschema.DBSchema` provides a bunch of useful functions for actions where the record is typed in
by the user. It's also useful when a part of the action requires user to type in some JSON document (which may be only
part of the record to be inserted). When requesting user input, usually the following steps would happen.

#. a document template is generated by the program as a file for user to fill in. Some fields are pre-filled, and some
   need human effort. Usually, the program would pause now for the user to finish, until Enter is pressed.
#. the user fills in the file, confirm that it's OK, and press Enter to continue.
#. the program loads in the file, and verify it against a JSON schema to make sure user has submitted a JSON document of
   valid format, and the program would probably do some post-processing

The first and third steps can be done easily with :class:`datasmart.core.dbschema.DBSchema`.

* The generation of a template can be done easily by putting a template file in the location specified as in
  :func:`datasmart.core.dbschema.DBSchema.get_template` and use
  :func:`datasmart.core.dbschema.DBSchema.post_process_template` to do any necessary postprocessing work.
* The validation of the user submitted document can be done by passing the text of it into
  :func:`datasmart.core.dbschema.DBSchema.generate_record`, and some (see :ref:`dbschema-things-not-specifiable`)
  post-processing can be done in :func:`datasmart.core.dbschema.DBSchema.post_process_record`, which is called in
  :func:`datasmart.core.dbschema.DBSchema.generate_record`. So :func:`datasmart.core.dbschema.DBSchema.generate_record`
  will return a record with the post-processing done.

Some post-processing steps, such as uploading files, is out of the scope for this class, which has no access to the
database (well if you insist you always can...). For these processing, they should be done in
:func:`datasmart.core.action.DBAction.perform`.
See :class:`datasmart.core.action.ManualDBActionWithSchema` for an example.

.. _JSON Schema: http://json-schema.org/
.. _BSON: http://bsonspec.org/
.. _JSON: http://www.json.org/
.. _jsl: http://jsl.readthedocs.org/


API reference of ``dbschema``
=============================

.. automodule:: datasmart.core.dbschema
   :members:
