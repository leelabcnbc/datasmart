************
Installation
************


System Requirements
===================

.. todo:: test which ``rsync`` version is needed.

#.  Linux or Mac OS X. Windows is not supported yet because I can't figure out string processing on Windows path names.
#.  Python 3.5.
#.  ``ssh`` and ``rsync``. Recent versions for them should do. Tested under Ubuntu 14.04.
#.  A list of packages, as in the ``requirements.txt`` file, shown below.

.. literalinclude:: /../requirements.txt

Set up python environment
-------------------------

An easy way to do this is as follows.

#.  first install `Anaconda`_ or `Miniconda`_. Versions for 2 and 3 both suffice.
    I assume that ``PATH`` for ``conda``-related programs (``conda``, ``activate``, etc.) are set properly.
    (This is the case if you install them in the usual way, unless you do things like quiet installation)
#.  ``git clone`` the whole repository, say under ``~/datasmart``.
#.  In the root directory of the repository, run ``./install_python_env.sh``

Certainly, if you are an experienced Python user, you can replicate the above steps without ``conda``.



Install actions
===============

To fully understand some terms and mentioned files in this section, read :ref:`installation_config_files` first.

The scripts mentioned in this section requires Python 3.5+ to run
(not necessarily the python in ``datasmart`` ``conda`` environment).

#.  In the repository directory, run ``install_config_core.py`` to install core configurations.
    Usually, the configuration for ``filetransfer`` and ``db`` should be modified.
#.  Then, for individual actions, run ``install_action.py`` to install them into separate folders.
    By install, it copies a set of configuration files and wrapper starting scripts for those actions.

    *  The syntax for ``install_action.py`` is ``install_action.py [DIRECTORY] [action1] [action2] ...``. For example,
       to install CORTEX related actions into ``~/Documents/datasmart-cortex``,
       run ``/install_action.py ~/Documents/datasmart-cortex leelab/cortex_exp leelab/cortex_exp_sorted``.
#.  After installing, please go to the ``config`` subdirectory to modify the default configurations as needed.

Usage
=====

In those directories created by ``install_action.py``, run ``start_*`` scripts to start the action,
that is, ``./start_*.sh``.

.. _installation_config_files:

Notes on configuration files
============================



There are some ``config.json`` files scattered under subdirectories of ``datasmart/config``.
They are configuration files for different modules and actions of DataSMART. They should be first installed
and then modified according to the specific settings of your environment. Before going through installation, let us
first see what configuration files look like.


Examples of configuration files
-------------------------------

One example here is the configuration file for database connection.

.. literalinclude:: /../datasmart/config/core/db/config.json
   :language: json

This configuration file defines how to connect to the MongoDB server. According to this file, the program will
connect to the MongoDB database on host ``127.0.0.1`` listening on port ``27017``. If ``authentication`` is ``true``,
then the user ``test`` with password ``test`` on authentication database ``auth_db`` will be used for authentication.

Check the documentation for separate modules and actions for their configuration files.


Configuration file resolution hierarchy
---------------------------------------

Clearly configuration files need to be changed from user to user.
DataSMART will read the config files for modules and actions under three different locations, from highest precedence
to lowest.

1. First, config files under the parent directory for invoked python script will be tried
   (more precisely, ``sys.path[0]``).
2. Then, config files under ``~/.datasmart`` will be tried.
3. Last, default config files under the repository will be tried.

For convenience, I created two files ``install_config_core.py`` and ``install_action.py`` to simplify installation of
configuration files. ``install_config_core.py`` installs all **core** configuration files under
``~/.datasmart``, and ``install_action.py`` installs **action-specific** configuration files under
separate project folders. You are welcome to violate this scheme as long as you know the underlying mechanism, which is
implemented in :func:`datasmart.core.util.load_config`. All configuration files should be written with UTF-8 encoding.



Setting up MongoDB
==================

.. todo:: more explanation on these scripts, especially how to restore.

DataSMART needs a MongoDB database to store metadata about recorded data and data processing actions. One easy to
install and maintain a (minimal, no replica set, no sharding) MongoDB database is using scripts under ``db_management``.
These scripts can help setting up a MongoDB instance within `Docker`_.

To use them, follow the steps below. They have been tested under Ubuntu 14.04.

#. Install `Docker`_.
#. change directory to ``db_management``.
#. edit ``envs.sh``.

   .. literalinclude:: /../db_management/envs.sh
      :language: bash

   * ``CONTAINER``: name of the Docker container.
   * ``DATA_CONTAINER``: name of the associated Docker data container. It can be left as is if
     you don't know what it is.
   * ``BACKUP_HOST_DIR``: where to store the backup files for database.
   * ``BACKUP_DOCKER_DIR``: the mapped location of ``BACKUP_HOST_DIR`` in Docker container. Don't need to change it.
   * ``IMAGE_NAME``: name of Docker image. It should be one from https://hub.docker.com/_/mongo/
#. Run ``./start_db.sh``. This will create backup directory, create data container and MongoDB container,
   run the MongoDB, and set up a superuser in the database as described in ``setup_admin_script.js``.
   Change the password immediately.
#. (optional) to do backup automatically, add a line in ``root``'s cron table like the following, where
   ``${XXX}`` should be replaced by the literal value of the root directory of DataSmart, and ``${BACKUP_HOST_DIR}``
   by the literal value of that variable in ``envs.sh``.

   .. code-block:: bash

      # m h  dom mon dow   command
        0 5  *   *   *     cd ${XXX}/db_management && XXX/db_management/backup_db.sh >> ${BACKUP_HOST_DIR}/log 2>&1

.. _Docker: https://www.docker.com/
.. _Anaconda: https://anaconda.org/
.. _Miniconda: http://conda.pydata.org/miniconda.html

