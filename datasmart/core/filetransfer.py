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
import shlex


class _SiteMappingSchema(jsl.Document):
    """ schema for site mapping. must be from remote to local
    """

    # use ``name`` argument of DocumentField to overcome keyword restriction in Python.
    _from = jsl.DocumentField(schemautil.filetransfer.FileTransferSiteRemote, name='from', required=True)
    _to = jsl.DocumentField(schemautil.filetransfer.FileTransferSiteLocal, name='to', required=True)


class _RemoteSiteConfigSchema(jsl.Document):
    """ schema for remote site mapping. should contain ssh username and ssh port.
    """
    ssh_username = jsl.StringField(required=True)
    # valid port is 1-65535, 0 usually meaning random port.
    ssh_port = jsl.IntField(required=True, minimum=1, maximum=65535)


# what options are available for ``local_fetch_option``.
_LOCAL_FETCH_OPTIONS = ["copy", "nocopy", "ask"]


class FileTransferConfigSchema(jsl.Document):
    """ schema for FileTransfer's config. Notice that push and fetch mappings are separate.
    This can be useful when we have a read-only (thus safe) mapping for fetch, and
    don't use mapping at all when push
    """
    # the default location of pushing / fetching files. can be either relative or absolute.
    local_data_dir = jsl.StringField(pattern=schemautil.StringPatterns.absOrRelativePathPatternOrEmpty,
                                     required=True)
    site_mapping_push = jsl.ArrayField(items=jsl.DocumentField(_SiteMappingSchema), unique_items=True, required=True)
    site_mapping_fetch = jsl.ArrayField(items=jsl.DocumentField(_SiteMappingSchema), unique_items=True, required=True)
    remote_site_config = jsl.DictField(additional_properties=jsl.DocumentField(_RemoteSiteConfigSchema), required=True)
    default_site = jsl.OneOfField([jsl.DocumentField(schemautil.filetransfer.FileTransferSiteLocal),
                                   jsl.DocumentField(schemautil.filetransfer.FileTransferSiteRemote)], required=True)
    quiet = jsl.BooleanField(required=True)

    # this stuff provides a default on whether copy or not for local fetch.
    local_fetch_option = jsl.StringField(enum=_LOCAL_FETCH_OPTIONS, required=True)


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
        # this works even when config['local_data_dir'] is absolute. see the official doc on
        # os.path.join to see why.
        config['local_data_dir'] = util.joinpath_norm(global_config['project_root'], config['local_data_dir'])

        if not os.path.exists(config['local_data_dir']):
            os.makedirs(config['local_data_dir'], exist_ok=True)

        # normalize site mapping.
        config['site_mapping_push'] = FileTransfer.normalize_site_mapping(config['site_mapping_push'])
        config['site_mapping_fetch'] = FileTransfer.normalize_site_mapping(config['site_mapping_fetch'])

        # normalize remote site config.
        # here site_path would be normalized.
        site_config_new = {}
        for site_path, site_conf in config['remote_site_config'].items():
            # I construct a temp remote site simply to get a normed path.
            site_path_new = FileTransfer._normalize_site({'local': False, 'path': site_path, 'prefix': '/'})['path']
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
        # check that if only has keys path local and prefix.
        site_new = site.copy()
        if 'append_prefix' in site_new:
            del site_new['append_prefix']
        if site_new['local']:
            # local site only has path.
            assert sorted(site_new.keys()) == sorted(['path', 'local'])
            # this will do even when ``site_new['path']`` is absolute.
            # See the Python doc for ``os.path.join`` for why this is true.
            site_new['path'] = util.joinpath_norm(global_config['project_root'], site_new['path'])
            assert os.path.isabs(site_new['path'])
        else:
            # remote site has prefix as well.
            assert sorted(site_new.keys()) == sorted(['path', 'prefix', 'local'])
            # convert everything to lower case and remove surrounding white characters.
            site_new['path'] = site_new['path'].lower().strip()
            site_new['prefix'] = os.path.normpath(site_new['prefix'])
            assert os.path.isabs(site_new['prefix'])

        return site_new

    def remove_dir(self, site: dict) -> None:
        """ remove an automatically generated directory by push.

        :param site: a site with 'append_prefix'. I won't do checking on this one, since it should be normalized.
        :return: None if everything is fine; otherwise throw Exception.
        """
        # make sure that append_prefix is not trivial.

        append_prefix = site['append_prefix']
        assert util.joinpath_norm(append_prefix) != util.joinpath_norm('')
        stdout_arg = subprocess.PIPE if self.config['quiet'] else None

        # remove is conceptually a push. so use mapping for push.
        site_mapped = self._site_mapping_push(site)

        if site_mapped['local']:
            rm_site_spec = util.joinpath_norm(site_mapped['path'], append_prefix)
            full_command = ['rm', '-rf', rm_site_spec]
        else:
            rm_site_spec_remote = util.joinpath_norm(site_mapped['prefix'], append_prefix)

            site_info = self.config['remote_site_config'][site_mapped['path']]

            rm_command = " ".join(['rm', '-rf', shlex.quote(rm_site_spec_remote)])
            full_command = ['ssh', site_info['ssh_username'] + '@' + site_mapped['path'],
                            '-p', str(site_info['ssh_port']), rm_command]
        if not self.config['quiet']:
            print(" ".join(full_command))
        subprocess.run(full_command, check=True, stdout=stdout_arg)

    def fetch(self, filelist: list, src_site: dict = None, relative: bool = False, subdirs: list = None,
              local_fetch_option=None, dryrun: bool = False, strip_prefix='') -> dict:
        """ fetch files from the site.

        it will fetch site/{prefix}/filelist{i} to
        'local_data_dir'/subdirs/(filelist{i} if relative else basename(filelist{i}))

        {prefix} is defined in config['site_config'] for remote sites, and empty for local site.

        :param strip_prefix: strip off one part of the path for files.
        :param filelist: a list of files to be fetched from the site.
        :param src_site: the site to fetch from. default is ``_config['default_site']``
        :param relative: copy full directory structure or just last part of each file path,
            like the same-named option in ``rsync``.
        :param subdirs: a list of path components under ``_config['local_data_dir']``.fetch would create them if needed.
        :param local_fetch_option: whether still fetch if it's local dir. By default, it will use the value
            set in :ref:`filetransfer-config-file`.
        :param dryrun: whether only perform a dry-run, without actual copying. Default to false.
        :return: throw Exception if anything wrong happens;
            otherwise a dict containing src, dest sites, filelist, and actual src and dest sites for dest.
            For fetch, actual src can be different from src due to mapping, and dest and actual dest are the same.
        """

        if src_site is None:
            src_site = self.config['default_site']
        if subdirs is None:
            subdirs = ['']
        if local_fetch_option is None:
            local_fetch_option = self.config['local_fetch_option']
        assert local_fetch_option in _LOCAL_FETCH_OPTIONS

        if strip_prefix:  # if it's not empty.
            strip_prefix = os.path.normpath(strip_prefix)

        # normalize the file list first.
        filelist = util.normalize_filelist_relative(filelist)
        savepath = util.joinpath_norm(self.config['local_data_dir'], self._reformat_subdirs(subdirs))
        # make sure it exists.
        os.makedirs(savepath, exist_ok=True)
        # get actual src site
        src_site = FileTransfer._normalize_site(src_site)
        src_actual_site = self._site_mapping_fetch(src_site)
        # if src_site is local yet original passed site is remote (so there's mapping)
        # we need to make the filelist relative.

        copy_flag = True

        if src_actual_site['local'] and (not src_site['local']):  # so there's mapping.
            if local_fetch_option == 'ask':
                a = input("do you want to copy the files? press enter to copy, enter anything then enter to not copy")
                if a:
                    copy_flag = False
                else:
                    copy_flag = True
            elif local_fetch_option == 'copy':
                copy_flag = True
            elif local_fetch_option == 'nocopy':
                copy_flag = False
            else:
                raise RuntimeError("can't be the case!")

        if copy_flag:
            dest_site = FileTransfer._normalize_site({"path": savepath, "local": True})
            ret_filelist = self._transfer(src_actual_site, dest_site,
                                          filelist, {"relative": relative, 'dryrun': dryrun,
                                                     'strip_prefix': strip_prefix})
        else:
            dest_site = src_actual_site
            # use actual filelist, since there's no fetch.
            ret_filelist = filelist

        return {'src': src_site, 'dest': dest_site, 'filelist': ret_filelist,
                'src_actual': src_actual_site, 'dest_actual': dest_site}

    def push(self, filelist: list, dest_site: dict = None, relative: bool = True, subdirs: list = None,
             dest_append_prefix: list = None, dryrun: bool = False) -> dict:
        """ push files to the site.

        it will push to site/{prefix}/{dest_append_prefix}/(filelist{i} if relative else basename(filelist{i})) from
        'local_data_dir'/subdirs/filelist{i}

        :param filelist: a list of files to be pushed to the site.
        :param dest_site: the site to push to. default is ``_config['default_site']``
        :param relative: copy full directory structure or just last part of each file path,
            like the same-named option in ``rsync``.
        :param subdirs: a list of path components under ``_config['local_data_dir']``. must exist.
        :param dest_append_prefix: a list of path components to append to usual dest dir
            see :ref:`filetransfer-site`.
        :param dryrun: whether only perform a dry-run, without actual copying. Default to false.
        :return: throw Exception if anything wrong happens;
            otherwise a dict containing src, dest sites, filelist, and actual src and dest sites for dest.
            For push, actual dest can be different from dest due to mapping, and src and actual src are the same.
        """
        if dest_site is None:
            dest_site = self.config['default_site']
        if subdirs is None:
            subdirs = ['']
        if dest_append_prefix is None:
            dest_append_prefix = ['']

        dest_append_prefix = util.joinpath_norm(*dest_append_prefix)
        # append prefix must be relative path.
        assert not (os.path.isabs(dest_append_prefix))
        if len(dest_append_prefix) == 2:
            assert dest_append_prefix != '..'
        elif len(dest_append_prefix) > 2:
            assert dest_append_prefix[:3] != '..' + os.path.sep
        # normalize the filelist first.
        filelist = util.normalize_filelist_relative(filelist)
        savepath = util.joinpath_norm(self.config['local_data_dir'], self._reformat_subdirs(subdirs))
        # check that subdir exists.
        assert os.path.exists(savepath), "{} doesn't exist!".format(savepath)

        for file in filelist:
            assert os.path.exists(util.joinpath_norm(savepath, file)), "the file {} must exist!".format(
                util.joinpath_norm(savepath, file)
            )

        # get actual site
        dest_site = FileTransfer._normalize_site(dest_site)
        dest_actual_site = self._site_mapping_push(dest_site)
        src_site = FileTransfer._normalize_site({"path": savepath, "local": True})
        ret_filelist = self._transfer(src_site, dest_actual_site,
                                      filelist, {"relative": relative,
                                                 "dryrun": dryrun,
                                                 "dest_append_prefix": dest_append_prefix})
        dest_site['append_prefix'] = dest_append_prefix
        dest_actual_site['append_prefix'] = dest_append_prefix
        return {'src': src_site, 'dest': dest_site, 'filelist': ret_filelist,
                'src_actual': src_site, 'dest_actual': dest_actual_site}

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

        if 'dest_append_prefix' not in options:
            options['dest_append_prefix'] = ''
        if 'strip_prefix' not in options:
            options['strip_prefix'] = ''

        assert not os.path.isabs(options['dest_append_prefix'])
        assert not os.path.isabs(options['strip_prefix'])

        if options['strip_prefix']:
            assert options['relative'], "with non trivial strip prefix, must be in relative mode!"

        # one of them must be local.
        assert src['local'] or dest['local']

        # construct the rsync command.
        # since I use -from-file option in rsync,  by default, it's relative without ``rsync_relative_arg``.
        rsync_relative_arg = "--relative" if options['relative'] else "--no-relative"
        # this will be filled in by rsync_ssh_arg_src or rsync_ssh_arg_dest if any of them is remote.
        rsync_ssh_arg = []

        # get the path of source and destination sites,  and get a ssh argument if necessary.
        rsync_src_spec, rsync_ssh_arg_src = self._get_rsync_site_spec(src)
        # provide an additional prefix for destination site (remote or local)
        rsync_dest_spec, rsync_ssh_arg_dest = self._get_rsync_site_spec(dest,
                                                                        append_prefix=options['dest_append_prefix'])
        # if there's any non-None ssh arg returned, there must be exactly one.
        assert (rsync_ssh_arg_src is None) or (rsync_ssh_arg_dest is None)
        if not (rsync_ssh_arg_src is None):
            rsync_ssh_arg = rsync_ssh_arg_src
        if not (rsync_ssh_arg_dest is None):
            rsync_ssh_arg = rsync_ssh_arg_dest

        # create a filelist for rsync's file-from option.
        # to and from can be different due to stripping prefix, and base name stuff.
        rsync_filelist_from, rsync_filelist_to = FileTransfer._get_rsync_filelist(filelist, options)

        # run the actual rsync if not dryrun.
        if options['dryrun']:
            rsync_dryrun_arg = ['--dry-run']
        else:
            rsync_dryrun_arg = []

        # create temp file for rsync_filelist_value.
        rsync_filelist_handle = tempfile.NamedTemporaryFile(mode='wt', delete=False)
        rsync_filelist_path = rsync_filelist_handle.name
        # add '/' in front in case we have file names starting with '#' or ';'
        # see http://samba.2283325.n4.nabble.com/comments-with-in-files-from-td2510187.html
        rsync_filelist_handle.writelines([os.sep + p + '\n' for p in rsync_filelist_from])
        rsync_filelist_handle.close()
        rsync_filelist_arg = "--files-from={}".format(rsync_filelist_path)

        # get the full rsync command.
        rsync_command = ["rsync", "-azvP",
                         rsync_relative_arg] + rsync_dryrun_arg + rsync_ssh_arg + [rsync_filelist_arg, rsync_src_spec,
                                                                                   rsync_dest_spec]

        # print the rsync command. this printed one may not work if you directly copy it, since special characters,
        # like spaces are not quoted properly.
        if not self.config['quiet']:
            print(" ".join(rsync_command))
        stdout_arg = subprocess.PIPE if self.config['quiet'] else None
        try:
            subprocess.run(rsync_command, check=True, stdout=stdout_arg)  # if not return 0, if fails.
        finally:
            # delete the filelist no matter what happens.
            os.remove(rsync_filelist_path)

        # return the canonical filelist on the dest. This should be relative for local dest, and absolute for remote.
        ret_filelist = util.normalize_filelist_relative(rsync_filelist_to, prefix=options['dest_append_prefix'])

        # strip prefix.

        return ret_filelist

    def _site_mapping_push(self, site: dict) -> dict:
        """ map site to the actual site used using ``_config['site_mapping_push']``

        :param site: the site to be mapped
        :return: a copy of the actual site
        """
        for map_pair_ in self.config['site_mapping_push']:
            if site == map_pair_['from']:
                return map_pair_['to'].copy()

        # return site itself if there's no mapping for it.
        return site.copy()

    def _site_mapping_fetch(self, site: dict) -> dict:
        """ map site to the actual site used using ``_config['site_mapping_fetch']``

        :param site: the site to be mapped
        :return: a **copy** of the actual site
        """
        for map_pair_ in self.config['site_mapping_fetch']:
            if site == map_pair_['from']:
                return map_pair_['to'].copy()

        # return site itself if there's no mapping for it.
        return site.copy()

    def _get_rsync_site_spec(self, site: dict, append_prefix: str = None) -> tuple:
        """get the rysnc arguments for a site.

        :param site: a site defined in class-level doc.
        :param append_prefix: additional prefix. this is primarily for dest site.
        :return:
        """
        if append_prefix is None:
            append_prefix = ''

        if site['local']:
            # for local site, we don't need additional argument for ssh, only append prefix if needed.
            rsync_site_spec = util.joinpath_norm(site['path'], append_prefix) + os.path.sep
            # sep is IMPORTANT to force it being a directory. This is useful when filelist only has ONE file.
            rsync_ssh_arg_site = None
        else:
            # for remote site, fetch the push prefix
            assert site['path'] in self.config['remote_site_config'], "this remote site must have config!"
            site_info = self.config['remote_site_config'][site['path']]
            prefix = site['prefix']
            rsync_site_spec = site_info['ssh_username'] + '@' + site['path'] + ':' + shlex.quote(
                util.joinpath_norm(prefix, append_prefix) + os.path.sep)
            # must quote since this string after ``:`` is parsed by remote shell. quote it to remove all wildcard
            # expansion... should test wild card to see if it works...
            rsync_ssh_arg_site = ['-e', "ssh -p {}".format(site_info['ssh_port'])]

        return rsync_site_spec, rsync_ssh_arg_site

    @staticmethod
    def _get_rsync_filelist(filelist: list, options: dict) -> tuple:
        """ get the filelist for rsync's files-from option.

        :param filelist: original file list.
        :param options: options passed into transfer.
        :return: a filelist to be written into a temp file for rsync to use as first element, and baselist as second.
        """

        if 'strip_prefix' in options:
            strip_prefix = options['strip_prefix']
        else:
            strip_prefix = ''

        # check that filenames don't contain weird characters, and get basename list.
        rsync_filelist_from = util.normalize_filelist_relative(filelist)

        # add strip_prefix.
        for x in rsync_filelist_from:
            assert x.startswith(strip_prefix)

        if strip_prefix:  # this needs to be added when strip_prefix is not empty.
            # +1 to ignore '/' in the beginning.
            rsync_filelist_from_second = [x[(len(strip_prefix) + 1):] for x in rsync_filelist_from]
            rsync_filelist_from = [strip_prefix + '/./' + x for x in rsync_filelist_from_second]
        else:
            rsync_filelist_from_second = rsync_filelist_from

        # this second part is canonical
        assert util.normalize_filelist_relative(rsync_filelist_from_second) == rsync_filelist_from_second
        # insertion of '/./' doesn't destroy anything.
        assert util.normalize_filelist_relative(rsync_filelist_from) == util.normalize_filelist_relative(filelist)

        if not options['relative']:
            rsync_filelist_to = [os.path.basename(p) for p in rsync_filelist_from]
        else:
            rsync_filelist_to = rsync_filelist_from_second

        # check for duplicate
        # for relative, no duplicate full path should exist
        # for non-relative, no duplicate basename should exist.
        FileTransfer._check_duplicate(rsync_filelist_to)
        return rsync_filelist_from, rsync_filelist_to

    @staticmethod
    def _check_duplicate(filelist: list) -> None:
        """ check that files are not duplicated.

        :param filelist: a list of strings
        :return: return None. raise error if there's any duplicate stuff.
        """
        duplicate_items = [item for item, count in collections.Counter(filelist).items() if count > 1]
        if duplicate_items:
            raise RuntimeError("duplicate files exist for non-relative mode: " + str(duplicate_items))
