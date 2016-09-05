import os
import string

from datasmart.core import global_config

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
    site_new = site.copy()
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
