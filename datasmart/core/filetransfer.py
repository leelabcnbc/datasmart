"""
The module for file transfer in DataSmart

"""
import collections
import os
import subprocess
import tempfile
from datasmart import global_config
from .base import Base
from . import util
from . import schemautil
import jsl




class _SiteMappingSchema(jsl.Document):
    """ schema for site mapping. must be from remote to local
    """
    _from = jsl.DocumentField(schemautil.FileTransferSiteRemote, name='from', required=True)
    _to = jsl.DocumentField(schemautil.FileTransferSiteLocal, name='to', required=True)


class _RemoteSiteConfigSchema(jsl.Document):
    """ schema for remote site mapping. should contain ssh username and ssh port.
    """
    ssh_username = jsl.StringField(required=True)
    ssh_port = jsl.IntField(required=True, minimum=1, maximum=65535)


class FileTransferConfigSchema(jsl.Document):
    """ schema for FileTransfer's config. Notice that push and fetch mappings are separate.
    This can be useful when we have a read-only (thus safe) mapping for fetch, and
    don't use mapping at all when push
    """
    # the default location of pushing / fetching files. can be either relative or absolute.
    local_data_dir = jsl.StringField(pattern=schemautil.SchemaUtilPatterns.absOrRelativePathPattern, required=True)
    site_mapping_push = jsl.ArrayField(items=jsl.DocumentField(_SiteMappingSchema), unique_items=True, required=True)
    site_mapping_fetch = jsl.ArrayField(items=jsl.DocumentField(_SiteMappingSchema), unique_items=True, required=True)
    remote_site_config = jsl.DictField(additional_properties=jsl.DocumentField(_RemoteSiteConfigSchema), required=True)
    default_site = jsl.OneOfField([jsl.DocumentField(schemautil.FileTransferSiteLocal),
                                   jsl.DocumentField(schemautil.FileTransferSiteRemote)],required=True)
    quiet = jsl.BooleanField(required=True)

    # this stuff provides a default on whether copy or not for local fetch.
    local_fetch_option = jsl.StringField(enum=["copy", "nocopy", "ask"], required=True)


class FileTransfer(Base):
    """ class for file transfer.

    Currently, file transfer is handled via ``rsync``.
    """

    config_path = ('core', 'filetransfer')

    def __init__(self, config=None) -> None:
        super().__init__(config)

    @staticmethod
    def normalize_config(config: dict) -> dict:
        """ normalize and validate paths in config.

        :param config: config dictionary
        :return: validated and normalized config dictionary.
        """

        # let's validate first...
        assert schemautil.validate(FileTransferConfigSchema.get_schema(), config)

        # normalize local save
        config['local_data_dir'] = util.joinpath_norm(global_config['project_root'], config['local_data_dir'])

        # normalize site mapping.
        config['site_mapping_push'] = FileTransfer.normalize_site_mapping(config['site_mapping_push'])
        config['site_mapping_fetch'] = FileTransfer.normalize_site_mapping(config['site_mapping_fetch'])

        # normalize remote site config.
        # here site_path would be normalized.
        site_config_new = {}
        for site_path, site_conf in config['remote_site_config'].items():
            site_path_new = FileTransfer._normalize_site({'local': False, 'path': site_path})['path']
            site_config_new[site_path_new] = site_conf
        config['remote_site_config'] = site_config_new

        # normalize default site.
        config['default_site'] = FileTransfer._normalize_site(config['default_site'])

        # assert again.
        assert schemautil.validate(FileTransferConfigSchema.get_schema(), config)
        return config

    def _reformat_subdirs(self, subdirs: list) -> str:
        """ check that subdirs is well-behaved, which means being relative and not higher than project root.

        :param subdirs: a list of path components under ``_config['local_data_dir']``.
        :return:
        """
        savepath_subdirs = util.joinpath_norm(*subdirs)
        assert not os.path.isabs(savepath_subdirs)
        # make sure savepath_subdirs is inside project root.
        # by checking that the common prefix of the local data dir and the subdir is local data dir.
        assert os.path.commonprefix([
            util.joinpath_norm(self.config['local_data_dir'], savepath_subdirs), self.config['local_data_dir']
        ]) == self.config['local_data_dir']
        return savepath_subdirs

    @staticmethod
    def normalize_site_mapping(site_mapping_old):
        # validate & normalize path in mapping.
        site_mapping_new = []
        for map_pair in site_mapping_old:
            assert (not map_pair['from']['local']) and (map_pair['to']['local'])  # must be remote to local map
            # I normalize ``from`` as well, since later we may have a way to normalize remote site.
            site_mapping_new.append(
                {'from': FileTransfer._normalize_site(map_pair['from']),
                 'to': FileTransfer._normalize_site(map_pair['to'])})
        return site_mapping_new

    @staticmethod
    def _normalize_site(site: dict) -> dict:
        """ return a new normalized site.
        primarily, we will normalize the path.

        :param site: a site as as defined in class level doc.
        :return: a normalized site.
        """
        site_new = site.copy()
        if site_new['local']:
            # this will do even when ``site_new['path']`` is absolute.
            # See the Python doc for ``os.path.join`` for why this is true.
            site_new['path'] = util.joinpath_norm(global_config['project_root'], site_new['path'])
            assert os.path.isabs(site_new['path'])
        else:
            # convert everything to lower case and remove surrounding white characters.
            site_new['path'] = site_new['path'].lower().strip()

        return site_new

    def fetch(self, filelist: list, site: dict = None, relative: bool = False, subdirs: list = None) -> dict:
        """ fetch files from the site.

        it will fetch site/{prefix}/filelist{i} to
        'local_data_dir'/subdirs/(filelist{i} if relative else basename(filelist{i}))

        {prefix} is defined in config['site_config'] for remote sites, and empty for local site.

        :param filelist: a list of files to be fetched from the site.
        :param site: the site to fetch from. default is ``_config['default_site']``
        :param relative: copy full directory structure or just last part of each file path,
            like the same-named option in ``rsync``.
        :param subdirs: a list of path components under ``_config['local_data_dir']``.fetch would create them if needed.
        :return: throw Exception if anything wrong happens;
            otherwise a dict containing src, dest sites and filelist for dest.
        """

        if site is None:
            site = self.config['default_site']
        if subdirs is None:
            subdirs = ['']

        savepath = util.joinpath_norm(self.config['local_data_dir'], self._reformat_subdirs(subdirs))
        # make sure it exists.
        os.makedirs(savepath, exist_ok=True)
        # get actual src site
        src_site = FileTransfer._normalize_site(self._site_mapping_fetch(site))
        # if src_site is local yet original passed site is remote (so there's mapping)
        # we need to make the filelist relative.
        if src_site['local'] and (not site['local']):
            filelist = [util.get_relative_path(p) for p in filelist]

        dest_site = FileTransfer._normalize_site({"path": savepath, "local": True})
        ret_filelist = self._transfer(src_site, dest_site,
                                      filelist, {"relative": relative})

        return {'src': src_site, 'dest': dest_site, 'filelist': ret_filelist}

    def push(self, filelist: list, site: dict = None, relative: bool = True, subdirs: list = None,
             dest_append_prefix: list = None) -> dict:
        """ push files to the site.

        it will push to site/{prefix}/{dest_append_prefix}/(filelist{i} if relative else basename(filelist{i})) from
        'local_data_dir'/subdirs/filelist{i}

        :param filelist: a list of files to be pushed to the site.
        :param site: the site to push to. default is ``_config['default_site']``
        :param relative: copy full directory structure or just last part of each file path,
            like the same-named option in ``rsync``.
        :param subdirs: a list of path components under ``_config['local_data_dir']``. must exist.
        :param dest_append_prefix: a list of path components to append to usual dest dir
        :return: throw Exception if anything wrong happens;
            otherwise a dict containing src, dest sites and filelist for dest.
        """
        if site is None:
            site = self.config['default_site']
        if subdirs is None:
            subdirs = ['']
        if dest_append_prefix is None:
            dest_append_prefix = ['']

        savepath = util.joinpath_norm(self.config['local_data_dir'], self._reformat_subdirs(subdirs))
        # check that subdir exists.
        assert os.path.exists(savepath)

        # the following is disabled, since site mapping is just a workaround for local processing.
        # get actual site
        # site_ = _normalize_site(_site_mapping(site))
        site = self._normalize_site(site)
        src_site = self._normalize_site({"path": savepath, "local": True})
        ret_filelist = self._transfer(src_site, site,
                                      filelist, {"relative": relative,
                                                 "dest_append_prefix": dest_append_prefix})

        return {'src': src_site, 'dest': site, 'filelist': ret_filelist}

    def _transfer(self, src: dict, dest: dict, filelist: list, options: dict) -> list:
        """ core function for data transfer. Currently implemented in ``rsync``.

        :param src: source site.
        :param dest: destination site.
        :param filelist:
        :param options:
        :return: the canonical filelist.
            this will return the normalized absolute path for remote site, and normalized relative path for local.
            Basically, ``dest['path'] + return value`` should give absolute path for files.
        """

        # one of them must be local.
        assert src['local'] or dest['local']

        # construct the rsync command.
        # since I use -from-file option in rsync,  by default, it's relative without ``rsync_relative_arg``.
        rsync_relative_arg = "--relative" if options['relative'] else "--no-relative"
        # this will be filled in by rsync_ssh_arg_src or rsync_ssh_arg_dest if any of them is remote.
        rsync_ssh_arg = []

        # get the path of source and destination sites,  and get a ssh argument if necessary.
        # for source site, (remote) prefix will be '/' automatically.
        rsync_src_spec, rsync_ssh_arg_src = self._get_rsync_site_spec(src, "/")

        # provide an additional prefix for destination site (remote or local)
        if "dest_append_prefix" in options:
            dest_append_prefix = options['dest_append_prefix']
        else:
            dest_append_prefix = ['']
        dest_append_prefix = util.joinpath_norm(*dest_append_prefix)
        # append prefix must be relative path.
        assert not (os.path.isabs(dest_append_prefix))
        rsync_dest_spec, rsync_ssh_arg_dest = self._get_rsync_site_spec(dest, append_prefix=dest_append_prefix)

        # if there's any non-None ssh arg returned, there must be exactly one.
        assert (rsync_ssh_arg_src is None) or (rsync_ssh_arg_dest is None)
        if not (rsync_ssh_arg_src is None):
            rsync_ssh_arg = rsync_ssh_arg_src
        if not (rsync_ssh_arg_dest is None):
            rsync_ssh_arg = rsync_ssh_arg_dest

        # create a filelist for rsync's file-from option.
        rsync_filelist_value, basename_list = self._get_rsync_filelist(filelist, src, options)

        # create temp file for rsync_filelist_value.
        rsync_filelist_handle = tempfile.NamedTemporaryFile(mode='wt', delete=False)
        rsync_filelist_path = rsync_filelist_handle.name
        rsync_filelist_handle.writelines([p + '\n' for p in rsync_filelist_value])
        rsync_filelist_handle.close()

        rsync_filelist_arg = "--files-from={}".format(rsync_filelist_path)

        # get the full rsync command.
        rsync_command = ["rsync", "-azvP",
                         rsync_relative_arg] + rsync_ssh_arg + [rsync_filelist_arg, rsync_src_spec, rsync_dest_spec]

        # print the rsync command.
        print(" ".join(rsync_command))
        stdout_arg = subprocess.PIPE if self.config['quiet'] else None
        subprocess.run(rsync_command, check=True, stdout=stdout_arg)  # if not return 0, if fails.

        # delete the filelist
        os.remove(rsync_filelist_path)

        # return the canonical filelist on the dest. This should be relative for local dest, and absolute for remote.
        ret_filelist = [util.get_relative_path(p) for p in
                        (rsync_filelist_value if options['relative'] else basename_list)]
        for p in ret_filelist:
            assert (not os.path.isabs(p)) and p and (p != '.') and (p != '..')

        # for remote case, we further append push prefix as well.
        if not dest['local']:
            dest_info = self.config['site_config'][dest['path']]
            prefix = dest_info['push_prefix']
        else:
            prefix = ''

        ret_filelist = [util.joinpath_norm(prefix, dest_append_prefix, p) for p in ret_filelist]

        for file in ret_filelist:
            if dest['local']:
                assert not os.path.isabs(file), "for local dest, file paths are all relative"
            else:
                assert os.path.isabs(file), "for remote dest, file paths are all absolute"
            assert file == os.path.normpath(file), "returned canonical filelist is not canonical!"

        return ret_filelist

    def _site_mapping_push(self, site: dict) -> dict:
        """ map site to the actual site used using ``_config['site_mapping_push']``

        :param site: the site to be mapped
        :return: the actual site
        """
        for map_pair_ in self.config['site_mapping_push']:
            if site == map_pair_['from']:
                return map_pair_['to']

        # return site itself if there's no mapping for it.
        return site


    def _site_mapping_fetch(self, site: dict) -> dict:
        """ map site to the actual site used using ``_config['site_mapping_fetch']``

        :param site: the site to be mapped
        :return: the actual site
        """
        for map_pair_ in self.config['site_mapping_fetch']:
            if site == map_pair_['from']:
                return map_pair_['to']

        # return site itself if there's no mapping for it.
        return site


    def _get_rsync_site_spec(self, site: dict, prefix: str = None, append_prefix: str = None) -> tuple:
        """get the rysnc arguments for a site.

        :param site: a site defined in class-level doc.
        :param prefix: the directory prefix after the site, before filelist.
        :param append_prefix: additional prefix. this is primarily for dest site.
        :return:
        """
        if append_prefix is None:
            append_prefix = ''
        if site['local']:
            # for local site, we don't need additional argument for ssh, only append prefix if needed.
            # also notice that prefix is ignored, since that's for remote only.
            # TODO. refactor the relationship between prefix and append_prefix.
            rsync_site_spec = util.joinpath_norm(site['path'], append_prefix)
            rsync_ssh_arg_site = None
        else:
            # for remote site, fetch the push prefix
            assert site['path'] in self.config['site_config'], "this remote site must have config!"
            site_info = self.config['site_config'][site['path']]
            if prefix is None:
                prefix = site_info['push_prefix']
            assert isinstance(prefix, str), "prefix must be string!"
            rsync_site_spec = site_info['ssh_username'] + '@' + site['path'] + ':' + util.joinpath_norm(prefix,
                                                                                                        append_prefix)
            rsync_ssh_arg_site = ['-e', "ssh -p {}".format(site_info['ssh_port'])]

        return rsync_site_spec, rsync_ssh_arg_site

    def _get_rsync_filelist(self, filelist: list, src: dict, options: dict) -> tuple:
        """ get the filelist for rsync's files-from option.

        :param filelist: original file list.
        :param src: src site
        :param options: options passed into transfer.
        :return: a filelist to be written into a temp file for rsync to use as first element, and baselist as second.
        """
        # check that filenames don't contain weird characters, and get basename list.
        rsync_filelist_value = [os.path.normpath(p) for p in filelist]
        for p in rsync_filelist_value:
            assert p.strip() == p, "no spaces around filename! this is good for your sanity."
        basename_list = [os.path.basename(p) for p in rsync_filelist_value]

        # make sure that there's no trivial file being copied.
        for b in basename_list:
            assert b and (b != '.') and (b != '..'), "no trival file name like empty, ., or ..!"

        if src['local']:
            # check that all paths are relative.
            for p in rsync_filelist_value:
                assert (not os.path.isabs(p)), "local file names must be relative"
        else:
            # check that all paths are absolute, since it's from remote.
            for p in rsync_filelist_value:
                assert os.path.isabs(p), "remote file names must be absolute"

        # check for duplicate
        # for relative, no duplicate full path should exist
        # for non-relative, no duplicate basename should exist.
        self._check_duplicate(rsync_filelist_value if options['relative'] else basename_list)

        return rsync_filelist_value, basename_list

    @staticmethod
    def _check_duplicate(filelist: list) -> None:
        """ check that files are not duplicated.

        :param filelist: a list of strings
        :return: return None. raise error if there's any duplicate stuff.
        """
        duplicate_items = [item for item, count in collections.Counter(filelist).items() if count > 1]
        if duplicate_items:
            raise RuntimeError("duplicate files exist for non-relative mode: " + str(duplicate_items))
