***********************
``filetransfer`` module
***********************

This module is concerned with non-metadata transfer in DataSMART. In DataSMART, the database only stores metadata, and
all the actual data files (``mat``, ``nev``, etc.) are stored externally, ideally in some dedicated file server owned
by the lab. The paths of data files are saved as metadata in database records.

The most important functions in this module are :func:`datasmart.core.filetransfer.FileTransfer.push` and
:func:`datasmart.core.filetransfer.FileTransfer.fetch`. Basically, what they do is pushing / fetching files
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

.. _filetransfer-site-append-prefix:

Site with ``append_prefix``
---------------------------

The destination sites returned by :func:`datasmart.core.filetransfer.FileTransfer.push` have an additional field
called ``append_prefix``, whose value is determined by argument ``dest_append_prefix`` in
:func:`datasmart.core.filetransfer.FileTransfer.push`. By default, ``dest_append_prefix`` would be ``None``, and
``append_prefix`` in that case would be ``.``. Otherwise, ``dest_append_prefix`` should be a list of strings,
``append_prefix`` being ``os.path.normpath(os.path.join(*dest_append_prefix))``. In any case, all files uploaded
will be put inside ``path`` / ``prefix`` (if this exists) / ``append_prefix``, hence its name.
This is useful when removing files uploaded through methods in :class:`datasmart.core.action.DBAction`, since these
methods would automatically put uploaded files in subfolders according the associated record's ``_id``.


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

.. _filetransfer-push-and-fetch:

How to use ``push`` and ``fetch``
=================================

This is a more detailed guide on how to use these two functions. For a more terse version, see
:func:`datasmart.core.filetransfer.FileTransfer.push` and :func:`datasmart.core.filetransfer.FileTransfer.push` below.


Common Arguments
----------------
These two functions have many arguments in common, which will be explained below first.

``filelist``
    a list of paths for files. They must be relative to ``local_data_dir``/``subdirs`` for push,
    and relative to ``path`` / ``prefix`` (if this exists) of ``src_site`` for fetch.

``src_site`` or ``dest_site``
    the source site for fetch or destination site for push. Must follow the the format in .. _filetransfer-site:,
    that is, a local site must have ``prefix`` and ``local=True``, and a remote site must have ``path``, ``prefix``,
    and ``local=False`` Additional properties would be rejected, except for ``append_prefix``, which
    will be discarded before checking the argument's fields.

``relative``
    this corresponds to ``--no-relative`` or ``--relative`` in ``rsync``.
    Basically, ``True`` (``--relative``) means preserving the directory structure originally in source site, that is,
    all path components before the actual base file names in ``filelist``, when copying files to the destination site.
    ``False`` (``--no-relative``) means flattening the directory structure. Notice that ``False`` can make the program
    complain if some files in ``filelist`` have identical basenames but live in different directories.

``subdirs``
    the additional prefix after the ``local_data_dir`` (see :ref:`filetransfer-config-file`), which is the default local
    directory for fetch and push. if ``subdirs`` is left unspecified, then files will be fetched directly inside
    ``local_data_dir``, and items in ``filelist`` are relative to ``local_data_dir`` for push. This can be useful, say
    the data processing action requires data from different sources, and you want to put them in different local
    sub directories.

``dryrun``
    whether simply returning the result that should be returned without actually copying.

``push``-specific arugments
---------------------------
``dest_append_prefix``
    this is explained in :ref:`filetransfer-site-append-prefix`. Basically, it adds another level of prefix to
    destination, but instead of changing ``prefix`` of the site, it modifies the filelist.


``fetch``-specific arugments
----------------------------
``local_fetch_option``
    whether still fetch if the source is local dir **after** mapping.
    (so it doesn't work if the source site is local from the beginning). This is solely used to deal with mapped drive
    problem.By default, it will use the value set in :ref:`filetransfer-config-file`.
    See :ref:`filetransfer-config-file` to see different options and their meanings.
    Notice that if this is true, then ``relative`` would clearly be discarded, since copying is not done at all.


return value
------------
the return value of both ``push`` and ``fetch`` is a dictionary with five fields.
Only ``src``, ``dest``, and ``filelist`` should be used and the other two are for debugging purpose.

``src``
    effective source site. This is same as ``src_actual`` for push, and maybe different for fetch due to mapping.
    For ``push``, it should be the site for ``local_data_dir``/``subdirs``. For ``fetch``, it's the ``src_site``
    passed in after normalization.

``src_actual``
    actual source site after mapping.

``dest``
    effective destination site. This is same as ``dest_actual`` for fetch, and maybe different for push due to mapping.
    For ``fetch``, it should be the site for ``local_data_dir``/``subdirs``
    if there's no local fetch optimization, and the local ``dest_actual`` if there is local fetch optimization.
    For ``push``, it's the ``dest_site`` passed in after normalization.

    In addition, the ``append_prefix`` field will be present if it's returned by ``push``.

``dest_actual``
    actual destination site after mapping.

    In addition, the ``append_prefix`` field will be present if it's returned by ``push``.

``filelist``
    for ``push``, ``dest`` (or ``dest_actual``) / ``filelist[i]`` are the locations of files relative
    to the destination site.

    for ``fetch``, ``dest`` (or ``dest_actual``) / ``filelist[i]`` are the locations of the files relative to
    ``local_data_dir``/``subdirs`` (or mapped local directory if there is local fetch optimization).


.. _filetransfer-config-file:

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



API reference of ``filetransfer``
=================================

.. automodule:: datasmart.core.filetransfer
   :members:


.. _NAS: https://en.wikipedia.org/wiki/Network-attached_storage
.. [#f1] Thanks `PC Zhou <http://zhoupc.github.io>`_ for valuable discussion on this matter. It makes me learn to place
    user requirement in the first place, instead of computer science geeks' fancy ideology.
