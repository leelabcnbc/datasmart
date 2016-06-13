************
Introduction
************

What is DataSMART
=================

DataSMART is design to manage data and processing pipelines in science labs.

Development
===========

Currently it is being developed by Yimeng Zhang in `Lee Lab`_.




Structure
=========

DataSMART uses MongoDB to manage data,
and users define **actions** to fetch data from the database, process the data, and push the data back to the DB.

DataSMART has two main parts: core modules and user-defined actions.

Core Modules
------------

The cores modules sit under :mod:`datasmart.core`.
They provide basic functions for users to write actions for data input, data processing, etc.

There are four main core modules:

:mod:`datasmart.core.db`
    Database module, responsible for connection and authentication with MongoDB database.
    Usually, users don't interact directly with this module.

:mod:`datasmart.core.filetransfer`
    File transfer module, responsible for pushing and fetching files related to data processing.
    Usually, users don't interact directly with this module.


:mod:`datasmart.core.dbschema`
    Database schema module, defining the format of each record in a MongoDB collection (table).
    Users have to define their own schemas for collections for different data processing needs.

:mod:`datasmart.core.action`
    Action module, defining some common action classes that correspond to common operations in a science lab.
    Users inherit from classes in this module to define their own action.


User-defined Actions
--------------------

Usually, users inherit from :mod:`datasmart.core.action` to define their own action for one collection (table) in the database,
and also inherit from :mod:`datasmart.core.dbschema` to define what each row in the collection looks like.
Most of the time, users don't directly inherit from :mod:`datasmart.core.action` but from its pre-defined subclasses,
since the base action class is too general to use. Pre-defined subclasses cover most use cases in a science lab, and users
only need to fill in the blanks that are specific to their needs.


Alternatives
============

There are many alternative systems for data management, including `DataJoint`_ and `G-Node`_.
However, some design decisions in these systems are inconsistent with the needs of `Lee Lab`_.


G-Node
    While it's technologically much more advanced than DataSMART, with HDF5, JSON, and RESTful API
    (see http://dx.doi.org/10.3389/fninf.2014.00032), etc.,
    We feel that it requires too much effort to adapt the existing tools in the lab to this platform. Our lab is mostly
    MATLAB-based, and changing the codebase and training our people would require too much.
    Also, in practice, there are some stability problems with G-Node pre se.
    For example, the Blackrock IO (for reading ``NEV`` and ``NSx`` files) for `Neo`_, which is used to represent
    data in G-Node, is not mature enough and probably buggy
    (see https://groups.google.com/forum/#!msg/neuralensemble/kUlwtYAoXAk/4gL2dHjvAgAJ the IO interface in the 0.3.3
    release of Neo is broken, and although there's a new one in the master branch, I don't want to use a dev version),
    compared to BlackRock's official MATLAB package `NPMK`_.

DataJoint
    There are two main problems with DataJoint IMO.

    #. You have to store all the data in the database itself. This causes three problems. 1) data
       files can be huge, and database can't hold them. 2) the data is saved in an opaque way, and it's only understood
       by DataJoint, and thus you can't fetch the data manually without DataJoint. 3) The type of data supported to be
       stored in DataJoint is limited, see
       `my discussion with authors of DataJoint <https://github.com/datajoint/datajoint-matlab/issues/49/>`_.
       On the contrary, DataSMART encourages people to only save links to your data files in the database, and provides
       mechanism to fetch them automatically from where they are located, say a FTP file server.
       This design can handle any data format and allow people to browse data manually if needed,
       because the data files are stored in a regular file system.
    #. The schema design has little flexibility in DataJoint, due to its tie to relational database. For example, to
       record the information about an experiment session, we may have to keep track the locations of multiple raw data
       files. Since it's impossible or difficult to save a list of file locations in a single row for a relational
       database, we have to create at least two tables to save metadata for experiment sessions, where one table keeps
       tracks of those singleton properties of an session, and the other keeps track of data files for sessions,
       each file being a row. In DataSMART, since we can save data in a JSON-like format,
       we can easily save all the information about one session in one table.
       The use of MongoDB in DataSMART makes schema design easier.


.. _Lee Lab: http://leelab.cnbc.cmu.edu
.. _DataJoint: http://datajoint.github.io
.. _G-Node: http://www.g-node.org
.. _Neo: http://neuralensemble.org/neo/
.. _NPMK: https://github.com/BlackrockMicrosystems/NPMK