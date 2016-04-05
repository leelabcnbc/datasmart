import jsl
from .stringpatterns import StringPatterns

# 4 types of sites, [Remote, Local] x [Auto, not auto]
class FileTransferSiteRemote(jsl.Document):
    path = jsl.StringField(format="hostname", required=True)
    local = jsl.BooleanField(enum=[False], required=True)
    prefix = jsl.StringField(pattern=StringPatterns.absPathPattern, required=True)


class FileTransferSiteLocal(jsl.Document):
    path = jsl.StringField(pattern=StringPatterns.absOrRelativePathPattern, required=True)
    local = jsl.BooleanField(enum=[True], required=True)


class FileTransferSiteRemoteAuto(FileTransferSiteRemote):
    append_prefix = jsl.StringField(pattern=StringPatterns.relativePathPattern, required=True)


class FileTransferSiteLocalAuto(FileTransferSiteLocal):
    append_prefix = jsl.StringField(pattern=StringPatterns.relativePathPattern, required=True)


# file list. only relative flavor is used.
FileListRelative = jsl.ArrayField(items=jsl.StringField(pattern=StringPatterns.relativePathPattern),
                                  min_items=1, unique_items=True, required=True)

# non-auto classes are usually input manually.
# 4 types of sites + only file list.
class FileTransferSiteAndFileListLocal(jsl.Document):
    site = jsl.DocumentField(FileTransferSiteLocal, required=True)
    filelist = FileListRelative


class FileTransferSiteAndFileListRemote(jsl.Document):
    site = jsl.DocumentField(FileTransferSiteRemote, required=True)
    filelist = FileListRelative


class FileTransferSiteAndFileListLocalAuto(jsl.Document):
    site = jsl.DocumentField(FileTransferSiteLocalAuto, required=True)
    filelist = FileListRelative


class FileTransferSiteAndFileListRemoteAuto(jsl.Document):
    site = jsl.DocumentField(FileTransferSiteRemoteAuto, required=True)
    filelist = FileListRelative

# any file list.
FileTransferSiteAndFileListAny = jsl.OneOfField([jsl.DocumentField(FileTransferSiteAndFileListLocal),
                                                 jsl.DocumentField(FileTransferSiteAndFileListRemote),
                                                 jsl.DocumentField(FileTransferSiteAndFileListLocalAuto),
                                                 jsl.DocumentField(FileTransferSiteAndFileListRemoteAuto)],
                                                required=True)

