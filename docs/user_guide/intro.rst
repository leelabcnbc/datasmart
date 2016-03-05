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



.. _Lee Lab: http://leelab.cnbc.cmu.edu
.. _DataJoint: http://datajoint.github.io
.. _G-Node: http://www.g-node.org
.. _Neo: http://neuralensemble.org/neo/
.. _NPMK: https://github.com/BlackrockMicrosystems/NPMK