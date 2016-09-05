"""
The module for file transfer in DataSmart

"""

import os
import shlex
import subprocess
import tempfile
import jsl
from datasmart.core.util.path import (normalize_site, normalize_site_mapping,
                                      get_rsync_filelist, get_site_mapping, reformat_subdirs, joinpath_norm,
                                      normalize_filelist_relative)
from datasmart.core.util.func import replace_none_args
from . import global_config
from . import schemautil
from .base import Base


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
        assert schemautil.validate(FileTransferConfigSchema.get_schema(),
                                   config), 'the config for filetransfer is invalid'

        # normalize local save
        # this works even when config['local_data_dir'] is absolute. see the official doc on
        # os.path.join to see why.
        config['local_data_dir'] = joinpath_norm(global_config['project_root'],
                                                 config['local_data_dir'])
        # create local dir
        if not os.path.exists(config['local_data_dir']):
            os.makedirs(config['local_data_dir'], exist_ok=True)

        # normalize site mapping.
        config['site_mapping_push'] = normalize_site_mapping(config['site_mapping_push'])
        config['site_mapping_fetch'] = normalize_site_mapping(config['site_mapping_fetch'])

        # normalize remote site config.
        # here site_path would be normalized.
        site_config_new = {}
        for site_path, site_conf in config['remote_site_config'].items():
            # I construct a temp remote site simply to get a normed path.
            site_path_new = normalize_site({'local': False, 'path': site_path, 'prefix': '/'})['path']
            site_config_new[site_path_new] = site_conf
        config['remote_site_config'] = site_config_new

        # normalize default site.
        config['default_site'] = normalize_site(config['default_site'])

        # assert again.
        assert schemautil.validate(FileTransferConfigSchema.get_schema(),
                                   config), 'the config for filetransfer is invalid'
        return config

    def remove_dir(self, site: dict) -> None:
        """ remove an automatically generated directory by push.

        :param site: a site with 'append_prefix'. I won't do checking on this one, since it should be normalized.
        :return: None if everything is fine; otherwise throw Exception.
        """
        append_prefix = site['append_prefix']
        # remove is conceptually a push. so use mapping for push.
        site_mapped = self._site_mapping_push(site)

        if site_mapped['local']:
            rm_site_spec = joinpath_norm(site_mapped['path'], append_prefix)
            full_command = ['rm', '-rf', rm_site_spec]
        else:
            rm_site_spec_remote = joinpath_norm(site_mapped['prefix'], append_prefix)

            site_info = self.config['remote_site_config'][site_mapped['path']]

            rm_command = " ".join(['rm', '-rf', shlex.quote(rm_site_spec_remote)])
            full_command = ['ssh', site_info['ssh_username'] + '@' + site_mapped['path'],
                            '-p', str(site_info['ssh_port']), rm_command]
        if not self.config['quiet']:
            print(" ".join(full_command))
            stdout_arg = None
        else:
            stdout_arg = subprocess.PIPE
        subprocess.run(full_command, check=True, stdout=stdout_arg)

    @staticmethod
    def _fetch_parse_copy(local_fetch_option):
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
        return copy_flag

    def _process_default_pars_fetch(self, src_site, subdirs,
                                    local_fetch_option, strip_prefix):
        src_site, subdirs, local_fetch_option = replace_none_args([src_site, subdirs, local_fetch_option],
                                                                  [self.config['default_site'], [''],
                                                                   self.config['local_fetch_option']])
        assert local_fetch_option in _LOCAL_FETCH_OPTIONS

        if strip_prefix:  # if it's not empty.
            strip_prefix = joinpath_norm(strip_prefix)
            # make sure it's not `.` or `..`.
            assert 'aaa' + os.path.sep + strip_prefix == joinpath_norm('aaa', strip_prefix)
        assert not (os.path.isabs(strip_prefix))
        return src_site, subdirs, local_fetch_option, strip_prefix

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
        src_site, subdirs, local_fetch_option, strip_prefix = self._process_default_pars_fetch(src_site, subdirs,
                                                                                               local_fetch_option,
                                                                                               strip_prefix)

        # normalize the file list first.
        filelist = normalize_filelist_relative(filelist)
        savepath = joinpath_norm(self.config['local_data_dir'],
                                 reformat_subdirs(subdirs, self.config['local_data_dir']))
        # make sure it exists.
        os.makedirs(savepath, exist_ok=True)
        # get actual src site
        src_site = normalize_site(src_site)
        src_actual_site = self._site_mapping_fetch(src_site)
        # if src_site is local yet original passed site is remote (so there's mapping)
        # we need to make the filelist relative.

        copy_flag = True

        if src_actual_site['local'] and (not src_site['local']):  # so there's mapping.
            copy_flag = FileTransfer._fetch_parse_copy(local_fetch_option)

        if copy_flag:
            dest_site = normalize_site({"path": savepath, "local": True})
            ret_filelist = self._transfer(src_actual_site, dest_site,
                                          filelist, {"relative": relative, 'dryrun': dryrun,
                                                     'strip_prefix': strip_prefix})
        else:
            dest_site = src_actual_site
            # use actual filelist, since there's no fetch.
            ret_filelist = filelist

        return {'src': src_site, 'dest': dest_site, 'filelist': ret_filelist,
                'src_actual': src_actual_site, 'dest_actual': dest_site}

    def _process_default_pars_push(self, dest_site, subdirs, dest_append_prefix):
        dest_site, subdirs, dest_append_prefix = replace_none_args([dest_site, subdirs, dest_append_prefix],
                                                                   [self.config['default_site'], [''], ['']])
        dest_append_prefix = joinpath_norm(*dest_append_prefix)
        # append prefix must be relative path.
        assert not (os.path.isabs(dest_append_prefix))
        # it should not go over current level, that is, not start with '..'
        # if it does, then `aaa` should disappear.
        if dest_append_prefix != joinpath_norm(*['']):  # special case for `.`
            assert 'aaa' + os.path.sep + dest_append_prefix == joinpath_norm('aaa', dest_append_prefix)

        return dest_site, subdirs, dest_append_prefix

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
        dest_site, subdirs, dest_append_prefix = self._process_default_pars_push(dest_site, subdirs, dest_append_prefix)
        # normalize the filelist first.
        filelist = normalize_filelist_relative(filelist)
        savepath = joinpath_norm(self.config['local_data_dir'],
                                 reformat_subdirs(subdirs, self.config['local_data_dir']))
        # check that subdir exists.
        assert os.path.exists(savepath), "{} doesn't exist!".format(savepath)

        for file in filelist:
            assert os.path.exists(
                joinpath_norm(savepath, file)), "the file {} must exist!".format(joinpath_norm(savepath, file))

        # get actual site
        dest_site = normalize_site(dest_site)
        dest_actual_site = self._site_mapping_push(dest_site)
        src_site = normalize_site({"path": savepath, "local": True})
        ret_filelist = self._transfer(src_site, dest_actual_site,
                                      filelist, {"relative": relative,
                                                 "dryrun": dryrun,
                                                 "dest_append_prefix": dest_append_prefix})
        dest_site['append_prefix'] = dest_append_prefix
        dest_actual_site['append_prefix'] = dest_append_prefix
        return {'src': src_site, 'dest': dest_site, 'filelist': ret_filelist,
                'src_actual': src_site, 'dest_actual': dest_actual_site}

    def _process_default_pars_transfer(self, options, src, dest):
        new_options = {
            'dest_append_prefix': '',
            'strip_prefix': '',
        }
        new_options.update(options)

        if new_options['strip_prefix']:
            assert new_options['relative'], "with non trivial strip prefix, must be in relative mode!"

        # one of them must be local.
        assert src['local'] or dest['local'], 'one of source and dest must be local'
        return new_options

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

        options = self._process_default_pars_transfer(options, src, dest)
        # construct the rsync command.
        # since I use -from-file option in rsync,  by default, it's relative without ``rsync_relative_arg``.
        rsync_relative_arg = "--relative" if options['relative'] else "--no-relative"
        # this will be filled in by rsync_ssh_arg_src or rsync_ssh_arg_dest if any of them is remote.


        # create a filelist for rsync's file-from option.
        # to and from can be different due to stripping prefix, and base name stuff.
        rsync_filelist_from, rsync_filelist_to = get_rsync_filelist(filelist, options)
        rsync_src_spec, rsync_dest_spec, rsync_ssh_arg = self._get_rysnc_ssh_spec(src, dest, options)
        # run the actual rsync if not dryrun.
        rsync_dryrun_arg = self._get_rysnc_dryrun_spec(options)

        # create temp file for rsync_filelist_value.
        with tempfile.NamedTemporaryFile(mode='wt', delete=False) as rsync_filelist_handle:
            rsync_filelist_path = rsync_filelist_handle.name
            # add '/' in front in case we have file names starting with '#' or ';'
            # see http://samba.2283325.n4.nabble.com/comments-with-in-files-from-td2510187.html
            rsync_filelist_handle.writelines([os.sep + p + '\n' for p in rsync_filelist_from])

        rsync_filelist_arg = "--files-from={}".format(rsync_filelist_path)

        # get the full rsync command.
        rsync_command = ["rsync", "-azvP",
                         rsync_relative_arg] + rsync_dryrun_arg + rsync_ssh_arg + [rsync_filelist_arg, rsync_src_spec,
                                                                                   rsync_dest_spec]

        # print the rsync command. this printed one may not work if you directly copy it, since special characters,
        # like spaces are not quoted properly.
        if not self.config['quiet']:
            print(" ".join(rsync_command))
            stdout_arg = None
        else:
            stdout_arg = subprocess.PIPE
        try:
            subprocess.run(rsync_command, check=True, stdout=stdout_arg)  # if not return 0, if fails.
        finally:
            # delete the filelist no matter what happens.
            os.remove(rsync_filelist_path)

        # return the canonical filelist on the dest. This should be relative for local dest, and absolute for remote.
        ret_filelist = normalize_filelist_relative(rsync_filelist_to,
                                                   prefix=options['dest_append_prefix'])

        # strip prefix.

        return ret_filelist

    def _site_mapping_push(self, site: dict) -> dict:
        """ map site to the actual site used using ``_config['site_mapping_push']``

        :param site: the site to be mapped
        :return: a copy of the actual site
        """
        return get_site_mapping(self.config['site_mapping_push'], site)

    def _site_mapping_fetch(self, site: dict) -> dict:
        """ map site to the actual site used using ``_config['site_mapping_fetch']``

        :param site: the site to be mapped
        :return: a **copy** of the actual site
        """
        return get_site_mapping(self.config['site_mapping_fetch'], site)

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
            rsync_site_spec = joinpath_norm(site['path'], append_prefix) + os.path.sep
            # sep is IMPORTANT to force it being a directory. This is useful when filelist only has ONE file.
            rsync_ssh_arg_site = None
        else:
            # for remote site, fetch the push prefix
            assert site['path'] in self.config['remote_site_config'], "this remote site must have config!"
            site_info = self.config['remote_site_config'][site['path']]
            prefix = site['prefix']
            rsync_site_spec = site_info['ssh_username'] + '@' + site['path'] + ':' + shlex.quote(
                joinpath_norm(prefix, append_prefix) + os.path.sep)
            # must quote since this string after ``:`` is parsed by remote shell. quote it to remove all wildcard
            # expansion... should test wild card to see if it works...
            rsync_ssh_arg_site = ['-e', "ssh -p {}".format(site_info['ssh_port'])]

        return rsync_site_spec, rsync_ssh_arg_site

    def _get_rysnc_ssh_spec(self, src, dest, options):
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
        return rsync_src_spec, rsync_dest_spec, rsync_ssh_arg

    def _get_rysnc_dryrun_spec(self, options):
        if options['dryrun']:
            rsync_dryrun_arg = ['--dry-run']
        else:
            rsync_dryrun_arg = []
        return rsync_dryrun_arg
