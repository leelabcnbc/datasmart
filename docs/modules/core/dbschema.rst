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


.. _JSON Schema: http://json-schema.org/
.. _BSON: http://bsonspec.org/
.. _JSON: http://www.json.org/

.. automodule:: datasmart.core.dbschema
   :members:
