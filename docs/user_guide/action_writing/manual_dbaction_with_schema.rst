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


General workflow of a ``ManualDBActionWithSchema``
==================================================

.. todo:: remove the database query since it's useless, and can be potentially confusing.

#. A (trivial) database query is performed. At the same time, the ``_id`` of the record to be inserted is generated.
#. A template for the record to be inserted is generated, usually named ``template.json`` under the local directory, and
   the action waits for the user to finish editing the template according to the specifics of the current experiment.
#. The action will perform some additional processing of the templated edited by the user.
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


How to write a ``ManualDBActionWithSchema``
===========================================



.. _CORTEX: http://www.nimh.nih.gov/labs-at-nimh/research-areas/clinics-and-labs/ln/shn/software-projects.shtml
.. _jsonschema: https://pypi.python.org/pypi/jsonschema

.. [#fbeforeinsertrecord] This will compromise the ability for the action to roll back. Well, in some sense, that's
   also true for any other method that users can override, since it's always possible to, say, connect to MongoDB
   using PyMongo directly in any of these methods. That's the freedom and responsiblity offered by Python.