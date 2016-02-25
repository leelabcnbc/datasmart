import jsl
import json


def get_schema_string(schema):
    return json.dumps(schema.get_schema(ordered=True), indent=2)


class SchemaUtilPatterns:
    gitHashPattern = "^[0-9a-f]{40}$"  # only allow lowercase to be more strict.
    absPathPattern = '(^(/[^/]+)+$)|(^/$)'
    relativePathPattern = '^([^/]+)(/[^/]+)*$'
    absOrRelativePathPattern = '(' + absPathPattern + ')' + '|' + '(' + relativePathPattern + ')'


class GitRepoRef(jsl.Document):
    repo_url = jsl.StringField(format="uri", required=True)
    repo_hash = jsl.StringField(pattern=SchemaUtilPatterns.gitHashPattern, required=True)


class FileTransferSiteRemote(jsl.Document):
    path = jsl.StringField(format="hostname", required=True)
    local = jsl.BooleanField(enum=[False], required=True)


class FileTransferSiteLocal(jsl.Document):
    path = jsl.StringField(pattern=SchemaUtilPatterns.absOrRelativePathPattern, required=True)
    local = jsl.BooleanField(enum=[True], required=True)


FileTransferSite = jsl.OneOfField([
    jsl.DocumentField(FileTransferSiteLocal),
    jsl.DocumentField(FileTransferSiteRemote)
])

FileListLocal = jsl.ArrayField(items=jsl.StringField(pattern=SchemaUtilPatterns.relativePathPattern),
                               min_items=1, unique_items=True, required=True)
FileListRemote = jsl.ArrayField(items=jsl.StringField(pattern=SchemaUtilPatterns.absPathPattern),
                                min_items=1, unique_items=True, required=True)


class FileTransferSiteAndFileListLocal(jsl.Document):
    site = jsl.DocumentField(FileTransferSiteLocal, required=True)
    filelist = FileListLocal


class FileTransferSiteAndFileListRemote(jsl.Document):
    site = jsl.DocumentField(FileTransferSiteRemote, required=True)
    filelist = FileListRemote
