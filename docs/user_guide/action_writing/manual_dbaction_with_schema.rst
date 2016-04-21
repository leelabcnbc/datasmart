************************************
writing ``ManualDBActionWithSchema``
************************************

This type of action is probably the first action to write in a data processing workflow. In the context of science data
management, it's useful for creating a record in the database storing all the metadata for collected data.

Examples
========

.. todo:: add some mouse related experiments

* You just performed a monkey experiment using `CORTEX`_, and want to create a record about this experiment, including
    #. what monkey was used.
    #. what recording files were generated, and where they are on some file server.
    #. the setup of the experiment. In the context of `CORTEX`_, this includes the set of ``tm``, ``cnd``, ``itm`` files
       used.
    #. some notes about the experiment, the same sort you would write down in the (physical) lab notebook.

The key features of an action inherited from :class:`datasmart.core.action.ManualDBActionWithSchema` are

#. No database query is needed.
#. Manual input heavy.
#. No much computation is done in this action (this can be done however).
#. One record at a time. Only one record will be inserted into the database after running the action.

.. _manual-db-action-with-schema-workflow:

General workflow of a ``ManualDBActionWithSchema``
==================================================

.. todo:: remove the database query since it's useless, and can be potentially confusing.

#. A (trivial) database query is performed. At the same time, the ``_id`` of the record to be inserted is generated.
#. A template for the record to be inserted is generated, usually named ``template.json`` under the local directory, and
   the action waits for the user to finish editing the template according to the specifics of the current experiment.
#. The action performs some additional processing of the template edited by the user.
    #. verify the form of the template follows some predefined JSON schema. Here, the Python package `jsonschema`_ is
       used.
    #. do some additional verification which is not possible by JSON schema. For example, in
       :mod:`datasmart.actions.leelab.cortex_exp`, number of stimuli for each condition should be the same. This type of
       complex verification is out of the scope of JSON schema.
       Also, some data type conversion will be done.
       For example, converting the string containing a valid timestamp into a native
       Python ``datetime.datetime`` object. These works should be done under
       :meth:`datasmart.core.dbschema.DBSchema.post_process_record`.
#.  The action performs some more processing that requires interaction with database and file server, or any arbitrary
    operation. [#fbeforeinsertrecord]_
    For example, in :mod:`datasmart.actions.leelab.cortex_exp`, the action will check that the
    list of recorded files submitted by the user indeed exist. This type of processing is specified under
    :meth:`datasmart.core.action.ManualDBActionWithSchema.before_insert_record`. In particular, code written here have
    easy access to wrapped file transfer methods.
#.  The action inserts the record into the database, and the action is done.





Concrete example
================

.. todo:: Summer finish **Concrete example**.


How to write a ``ManualDBActionWithSchema`` based action
========================================================

General structure of the code for the action
--------------------------------------------

Generally speaking, there are three classes to defined.

#.  the actual action class inherited from :class:`datasmart.core.action.ManualDBActionWithSchema`. The logic for (more
    general) post processing of the edited template (step 4 in :ref:`manual-db-action-with-schema-workflow`) is defined
    here.
#.  a schema helper class inherited from :class:`datasmart.core.dbschema.DBSchema`. The logic for (easy) post processing
    of the edited template (step 3 in :ref:`manual-db-action-with-schema-workflow`) is defined here.
#.  a JSON schema definition class inherited from ``jsl.Document``. This in theory can be defined inside
    the schema helper class, but maybe making it a separate class gives cleaner code.

Schema definition
-----------------
First of all, it's strongly recommended to define strictly how a database record should look like, that is, a schema for
the records to be inserted. The schema is defined using JSON schema via `jsonschema`_. Check
:class:`datasmart.actions.leelab.corex_exp.CortexExpSchemaJSL` for an example.


Schema class Definition
-----------------------
The JSON schema defined above need to be somehow linked to the ``ManualDBActionWithSchema`` action class. In DataSMART,
this is done via a intermediate schema class inherited from :class:`datasmart.core.dbschema.DBSchema`. As an example,
:class`datasmart.actions.leelab.corex_exp.CortexExpSchema` has the following things defined.

#.  :attr:`datasmart.core.dbschema.DBSchema.schema_path`. This should best match
    :attr:`datasmart.core.base.Base.config_path`, since this is the path where the template file will be read (unless
    your template is embedded in the code or generated on-the-fly, but still it's good to match them for doc purpose).
#.  :meth:`datasmart.core.dbschema.DBSchema.get_schema`. This defines where to read the JSON schema.
    By default, it will read file ``schema.json`` under :attr:`datasmart.core.dbschema.DBSchema.schema_path`,
    but it's recommended to override this method and specify the
    schema to be obtained from the JSON schema definition class directly, since raw JSON schema files are more difficult
    to write or maintain.
#.  :meth:`datasmart.core.dbschema.DBSchema.get_template`. This is the method to get the text of the record template.
    By default, it will read the template from ``template.json``
    under :attr:`datasmart.core.dbschema.DBSchema.schema_path`,
    run :meth:`datasmart.core.dbschema.DBSchema.post_process_template` against it, verify it against the schema.
    I don't recommend changing this method at all, since there's some verification logic in the default method.
    However, if you really need some mechanism to generate the template on the fly without any concrete template file to
    begin with, you can simply implement all these in :meth:`datasmart.core.dbschema.DBSchema.post_process_template` and use an
    empty template file for ``template.json``.
#.  :meth:`datasmart.core.dbschema.DBSchema.post_process_template`. This method does some post processing the raw template
    file before presenting it to the user. For example,
    in :meth:`datasmart.actions.leelab.cortex_exp.CortexExpSchema.post_process_template`, the current timestamp, and some
    info about the git repository for experiments is plugged into the raw template file.
#.  :meth:`datasmart.core.dbschema.DBSchema.post_process_record` This handles the (easy) post processing logic after the
    user has edited the template. See :meth:`datasmart.actions.leelab.cortex_exp.CortexExpSchema.post_process_record` for
    an example.

Action class definition
-----------------------

#.  :attr:`datasmart.core.action.DBAction.table_path` the ``(database, collection)`` tuple specifying where to insert
    the record in the database.
#.  :attr:`datasmart.core.base.Base.config_path` location of the all related config files.
#.  :attr:`datasmart.core.action.DBActionWithSchema.dbschema` should be set to the helper schema class defined.
#.  :meth:`datasmart.core.action.ManualDBActionWithSchema.before_insert_record`
    defines the (more general) post processing before inserting the record.


.. _CORTEX: http://www.nimh.nih.gov/labs-at-nimh/research-areas/clinics-and-labs/ln/shn/software-projects.shtml
.. _jsonschema: https://pypi.python.org/pypi/jsonschema

.. [#fbeforeinsertrecord] This will compromise the ability for the action to roll back. Well, in some sense, that's
   also true for any other method that users can override, since it's always possible to, say, connect to MongoDB
   using PyMongo directly in any of these methods. That's the freedom and responsiblity offered by Python.