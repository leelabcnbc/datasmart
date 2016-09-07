import os
import string
import collections
from copy import deepcopy
from datasmart.core import global_config
from datasmart.core.schemautil.filetransfer import FileTransferSiteAny, FileTransferSiteStandard
from datasmart.core.schemautil import validate

_valid_chracters = set(string.printable) - set('\t\n\r\v\f')


def joinpath_norm(path, *paths):
    """ os.path.join plus os.path.normpath. Same interface as os.path.join.

    :param path:
    :param paths:
    :return: normalized joined path.
    """
    s = os.path.normpath(os.path.join(path, *paths))
    assert s == os.path.normpath(s)
    # make sure unique unicode normalization.
    for c in s:
        assert c in _valid_chracters, "path {} has invalid character {}".format(s, c)
    return s


def normalize_site(site: dict) -> dict:
    """ return a new normalized site.
    primarily, we will normalize the path.

    :param site: a site as as defined in class level doc.
    :return: a normalized site.
    """
    # check that if only has keys path local and prefix.
    site_new = deepcopy(site)

    assert validate(FileTransferSiteAny.get_schema(), site_new)

    if 'append_prefix' in site_new:
        del site_new['append_prefix']

    if site_new['local']:
        # this will do even when ``site_new['path']`` is absolute.
        # See the Python doc for ``os.path.join`` for why this is true.
        site_new['path'] = joinpath_norm(global_config['project_root'], site_new['path'])
    else:
        # make sure it only has ASCII characters. Don't deal with Unicode.
        for c in site_new['path']:
            assert c in string.printable
        # convert everything to lower case and remove surrounding white characters.
        site_new['path'] = site_new['path'].lower().strip()
        site_new['prefix'] = joinpath_norm(site_new['prefix'])
    assert validate(FileTransferSiteStandard.get_schema(), site_new)
    return site_new


def normalize_site_mapping(site_mapping_old):
    # validate & normalize path in mapping.
    site_mapping_new = []
    for map_pair in site_mapping_old:
        assert (not map_pair['from']['local']) and (map_pair['to']['local'])  # must be remote to local map
        # I normalize ``from`` as well, since later we may have a way to normalize remote site.
        site_mapping_new.append(
            {'from': normalize_site(map_pair['from']),
             'to': normalize_site(map_pair['to'])})
    return site_mapping_new


def filename_more_check(p):
    assert p.strip() == p, "no spaces around filename! this is good for your sanity."
    assert not os.path.isabs(p), "file paths are all relative"
    b = os.path.basename(p)
    assert '/' not in b, 'directory separator should not exist in file name!'
    assert b and (b != '.') and (b != '..'), "no trival file name like empty, ., or ..!"


def normalize_filelist_relative(filelist: list, prefix='') -> list:
    """ normalize a list of relative file paths, and check that paths are well-behaved.

    :param filelist: a list of relative file paths
    :param prefix: an optional preffix
    :return: same file list, with paths normalized.
    """
    assert len(filelist) > 0

    ret_filelist = [joinpath_norm(prefix, p) for p in filelist]
    for p in ret_filelist:
        filename_more_check(p)
    return ret_filelist


def check_duplicate(filelist: list) -> None:
    """ check that files are not duplicated.

    :param filelist: a list of strings
    :return: return None. raise error if there's any duplicate stuff.
    """
    duplicate_items = [item for item, count in collections.Counter(filelist).items() if count > 1]
    if duplicate_items:
        raise RuntimeError("duplicate files exist for non-relative mode: " + str(duplicate_items))


def get_rsync_filelist(filelist: list, options: dict) -> tuple:
    """ get the filelist for rsync's files-from option.

    :param filelist: original file list.
    :param options: options passed into transfer.
    :return: a filelist to be written into a temp file for rsync to use as first element, and baselist as second.
    """

    if 'strip_prefix' in options:
        strip_prefix = options['strip_prefix']
    else:
        strip_prefix = ''

    # get from list
    # check that filenames don't contain weird characters, and get basename list.
    rsync_filelist_from = normalize_filelist_relative(filelist)

    # add strip_prefix.
    for x in rsync_filelist_from:
        assert x.startswith(strip_prefix), 'file {} does not start with prefix `{}`'.format(x, strip_prefix)

    # revise from list based on strip, and get files on remote host (relative)
    if strip_prefix:  # this needs to be added when strip_prefix is not empty.
        # +1 to ignore '/' in the beginning.
        rsync_filelist_from_second = [x[(len(strip_prefix) + 1):] for x in rsync_filelist_from]
        # adding a `.` to help rsync decide when to strip.
        # for example, rsync -avR /foo/./bar/baz.c remote:/tmp/
        # would create /tmp/bar/baz.c on the remote machine.
        # see <https://www.samba.org/ftp/rsync/rsync.html>
        rsync_filelist_from = [strip_prefix + '/./' + x for x in rsync_filelist_from_second]
    else:
        rsync_filelist_from_second = rsync_filelist_from

    # `rsync_filelist_from_second` is the list of files that will appear on remote host.
    # (in relative mode)
    assert normalize_filelist_relative(rsync_filelist_from_second) == rsync_filelist_from_second

    if not options['relative']:
        rsync_filelist_to = [os.path.basename(p) for p in rsync_filelist_from]
    else:
        rsync_filelist_to = rsync_filelist_from_second

    # check for duplicate
    # for relative, no duplicate full path should exist
    # for non-relative, no duplicate basename should exist.
    check_duplicate(rsync_filelist_to)
    return rsync_filelist_from, rsync_filelist_to


def get_site_mapping(mapping_dict, site):
    assert validate(FileTransferSiteStandard.get_schema(), site)
    for map_pair_ in mapping_dict:
        if site == map_pair_['from']:
            return deepcopy(map_pair_['to'])

    # return site itself if there's no mapping for it.
    return deepcopy(site)


def reformat_subdirs(subdirs: list, local_data_dir: str) -> str:
    """ check that subdirs is well-behaved, which means being relative and not higher than project root.

    :param subdirs: a list of path components under ``_config['local_data_dir']``.
    :return:
    """
    savepath_subdirs = joinpath_norm(*subdirs)
    assert not os.path.isabs(savepath_subdirs)
    # make sure savepath_subdirs is inside project root.
    # by checking that the common prefix of the local data dir and the subdir is local data dir.
    assert os.path.commonprefix([joinpath_norm(local_data_dir, savepath_subdirs), local_data_dir]) == local_data_dir
    return savepath_subdirs
