***********************
``filetransfer`` module
***********************

This module is concerned with non-metadata transfer in DataSMART. In DataSMART, the database only stores metadata, and
all the actual data files (``mat``, ``nev``, etc.) are stored externally, ideally in some dedicated file server owned
by the lab. The paths of data files are saved as metadata in database records.

The most important functions in this module are :func:`datasmart.core.filetransfer.Filetransfer.push` and
:func:`datasmart.core.filetransfer.Filetransfer.fetch`. Basically, what they do is pushing / fetching files
between two :ref:`filetransfer-site`.

.. _filetransfer-site:

Site
====
A site defines a *directory*, which can be either in the local computer, or in some remote server.
Examples are as follows.

.. code-block:: json

    {
        "path": "raptor.cnbc.cmu.edu",
        "prefix": "/opt/data/home/leelab",
        "local": false
    }
    {
        "path": "/Users/yimengzh/datajoin_data",
        "local": true
    }

The first example defines a *remote* site, and second example a *local* site. Being local or not is distinguished by
the ``local`` field.

#.  for a local site, the ``path`` field should be a locally accessible directory
    (relative or absolute paths are both fine).
#.  for a remote site, the ``prefix`` field field shuold be a valid absolute path pointing to a directory on server
    ``path``.

Relative Path
-------------
When using relative path in a site (as well as all other places in DataSMART),
it's always relative to the ``project_root`` in :func:`datasmart.core.base.Base.global_config`.


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

Config File
===========
a demo config file for the ``filetransfer`` module looks like the following.

.. literalinclude:: /../datasmart/config/core/filetransfer/config.json
    :language: json

The fields are defined as follows.

``local_data_dir``
    the default destination directory for fetch and source directory for push.

``site_mapping_fetch``
    the mapping for fetch. each entry in the list must have a remote ``from`` and a local ``to``.

``site_mapping_push``
    similar as ``site_mapping_fetch``, but for push. The reason to have separate settings for push and fetch is
    to be more flexible. One use case is that for fetch, the directories are mounted with read-only permission, and
    for push, we push directory directory remotely without the local mount. This can avoid file copying and minimize the
    risk of (unintentionally) modifying files.

``remote_site_config``
    this is a dictionary (in the Python sense) saving remote server's parameters. currently,
    ssh username and ssh port are required.

``default_site``
    the default source site for fetch and destination site for push.

``quiet``
    whether showing all the details of file transmission.

``local_fetch_option``
    when the fetch source site is local (after doing the mapping), users can determine how to handle this. Three options
    are:

    * ``copy`` copy. This should be the case if you will change the files later.
    * ``nocopy`` don't copy. This is ideal for read-only files.
    * ``ask`` ask for user explicitly before transmission.


.. automodule:: datasmart.core.filetransfer
   :members:


.. _NAS: https://en.wikipedia.org/wiki/Network-attached_storage
.. [#f1] Thanks `PC Zhou <http://zhoupc.github.io>`_ for valuable discussion on this matter. It makes me learn to place
    user requirement in the first place, instead of computer science geeks' fancy ideology.
