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



Structure of a database-related action
======================================

In practice, the abstraction provided by the base :class:`datasmart.core.action.Action` is too high to be useful.
Therefore, a more concrete action class :class:`datasmart.core.action.DBAction` is developed to suit the everyday need
of data processing.



.. automodule:: datasmart.core.action
   :members:
