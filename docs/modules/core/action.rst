*****************
``action`` module
*****************

An action in DataSMART corresponds to an actual data processing step in a data analysis pipeline.
Example actions (or data processing steps) are:

#. upload spiking neural data along with metadata
#. do automatic spike sorting on raw data.
#. do alignment of Calcium imaging data.


Two phases in an action
=======================

:class:`datasmart.core.action.Action` defines the action on the most abstract level. It models every possible data
processing step as a two-phase process: **prepare** and **perform**. The idea of having this phase
is that a data processing step is usually composed of two parts:

   #. finding the correct files, parameters, etc. This part has some manual interference, and requires the attention
      of humans.
   #. running the actual processing. This part is automatic, and requires machine time alone.

**prepare** and **perform** correspond to these two steps. After doing once, the progress made in the **prepare** step
will be saved on disk, and in case the machine fails on the **perform** stage, the program will simply load the previous
**prepare** result, do the **perform** step, without asking users to repeat their hard work.

The main method to use for an action is :func:`datasmart.core.action.Action.run`, which has the following structure.

.. literalinclude:: /../datasmart/core/action.py
   :pyobject: Action.run

The structure of this function is self-explanatory. :func:`datasmart.core.action.Action.is_finished` returns ``True``
if and only if the action has been performed successfully, and :func:`datasmart.core.action.Action.is_prepared` returns
``True`` if and only if the action has been prepared successfully.

In addition, every action has an optional :func:`datasmart.core.action.Action.revoke` method to reverse the effects
of a performed action.

Structure of a database-related action
======================================

In practice, the abstraction provided by the base :class:`datasmart.core.action.Action` is too high to be useful.
Therefore, a more concrete action class :class:`datasmart.core.action.DBAction` is developed to suit the everyday need
of data processing.

**prepare** phase of ``DBAction``
---------------------------------
In the **prepare** phase, the action will perform some database query and collect all the information
it needs to **perform**. First of all, it will generate a query snippet template ``query_template.py`` specified via
:func:`datasmart.core.action.DBAction.generate_query_doc_template`.
Every subclass of :class:`datasmart.core.action.DBAction` should override this method if that action needs some query
from database (exceptions: manual data input, manual file upload, etc. do not need query)
The information in this template will help the user in formulating their specific query. Here, any code can be run,
and the user is expected to save everything they need from query in a variable called ``result``.

.. todo:: add a non-trival query snippet.

after getting the query result, the result will be validated via (overridden)
:func:`datasmart.core.action.DBAction.validate_query_result`, and any further preparing work should be done via
(overridden) :func:`datasmart.core.action.DBAction.prepare_post`, which will be passed in the ``result`` from query, and
will return a dictionary representing the final **prepare** result.
This dictionary must have a field called ``result_ids``, which is a list of ``_id``'s of the records to be inserted.
``_id`` is the id field for a MongoDB record, and it must have type ``ObjectId``
(see http://api.mongodb.org/python/current/api/bson/objectid.html ). This design makes sure that in case **perform** is
partially executed, the partially inserted result can be removed from the database and the file server [#f1]_.


.. [#f1] Currently, for the files, only the files associated with an inserted record can be removed.
   So to remove partially uploaded files, you need to first finish the action and then remove.
   The reason of this is that we always assume that there is only one database to interact with, yet there are possibly
   more than one file server to put files. One improvement is that no matter what, we always try to remove files from the
   default file server. As long as people always upload to the only file server, it would work.

After all these, the result returned by :func:`datasmart.core.action.DBAction.prepare_post`
will be saved in ``prepare_result.p``, and the **prepare** phase is done.

**perform** phase of ``DBAction``
---------------------------------
In the **process** phase, the action should perform the bulk of computation, given the result of **prepare** phase.
:func:`datasmart.core.action.DBAction.perform` must be overridden by a subclass.




API reference of ``action``
===========================

.. automodule:: datasmart.core.action
   :members:
