***********************
``filetransfer`` module
***********************

This module is concerned with non-metadata transfer in DataSMART. In DataSMART, the database only stores metadata, and
all the actual data files (``mat``, ``nev``, etc.) are stored externally, ideally in some dedicated file server owned
by the lab. The paths of data files are saved as metadata in database records.

The most important functions in this module are :func:`datasmart.core.filetransfer.Filetransfer.push` and
:func:`datasmart.core.filetransfer.Filetransfer.fetch`. Basically, what they do is pushing / fetching files
between two :ref:`filetranser_site`.

.. _filetransfer_site:

Site
====
A site defines a directory, which can be either in the local computer, or in some remote server.

Site mapping
============
Sometimes, a local site is not actually local: an apparently local directory can actually be located in some remote
hard drive. This kind of mapping exists for at least two reasons.

#.  for some read-only large data files, users don't want to download before being able to process them.
    This is especially the case for some new data formats, such as HDF5, which only loads data as needed.
    With mapped directory, users who only want to examine a small portion of the data file can save a lot of bandwidth
    and time (assuming that users are wise enough not to modify the file; or this permission stuff can be set when mapping
    the directory itself). [#f1]_
#.  for some remote file server products, such as `NAS`_, it's much easier to map drives than communicating the server
    with ``rsync`` + ``ssh``, which is only available for root for many NAS products.
    This means while files on the server are available for every one with (limited) access to NAS, users always have to
    operate with them locally.

.. automodule:: datasmart.core.filetransfer
   :members:


.. _NAS: https://en.wikipedia.org/wiki/Network-attached_storage
.. [#f1] Thanks PC Zhou (zhoupc.github.io) for valuable discussion on this matter.
