import jsl
import json
import jsonschema
from jsonschema import FormatChecker, Draft4Validator
from jsonschema.exceptions import ValidationError, SchemaError


def validate(schema, record):
    try:
        jsonschema.validate(instance=record, schema=schema, format_checker=FormatChecker(),
                            cls=Draft4Validator)
    except (ValidationError, SchemaError) as e:
        print(e)
        return False
    return True


def get_schema_string(schema):
    return json.dumps(schema.get_schema(ordered=True), indent=2)


class SchemaUtilPatterns:
    gitHashPattern = "^[0-9a-f]{40}$"  # only allow lowercase to be more strict.
    absPathPattern = '(^(/[^/]+)+$)|(^/$)'
    relativePathPattern = '^([^/]+)(/[^/]+)*$'
    absOrRelativePathPattern = '(' + absPathPattern + ')' + '|' + '(' + relativePathPattern + ')'
    absOrRelativePathPatternOrEmpty = '(' + absPathPattern + ')' + '|' + '(' + relativePathPattern + ')' + '|(^$)'

class GitRepoRef(jsl.Document):
    repo_url = jsl.StringField(format="uri", required=True)
    repo_hash = jsl.StringField(pattern=SchemaUtilPatterns.gitHashPattern, required=True)


class FileTransferSiteRemote(jsl.Document):
    path = jsl.StringField(format="hostname", required=True)
    local = jsl.BooleanField(enum=[False], required=True)
    prefix = jsl.StringField(pattern=SchemaUtilPatterns.absPathPattern, required=True)


class FileTransferSiteLocal(jsl.Document):
    path = jsl.StringField(pattern=SchemaUtilPatterns.absOrRelativePathPattern, required=True)
    local = jsl.BooleanField(enum=[True], required=True)


class FileTransferSiteRemoteAuto(FileTransferSiteRemote):
    append_prefix = jsl.StringField(pattern=SchemaUtilPatterns.relativePathPattern, required=True)


class FileTransferSiteLocalAuto(FileTransferSiteLocal):
    append_prefix = jsl.StringField(pattern=SchemaUtilPatterns.relativePathPattern, required=True)


FileTransferSiteBoth = jsl.OneOfField([
    jsl.DocumentField(FileTransferSiteLocal),
    jsl.DocumentField(FileTransferSiteRemote)
],required=True)

FileListRelative = jsl.ArrayField(items=jsl.StringField(pattern=SchemaUtilPatterns.relativePathPattern),
                                  min_items=1, unique_items=True, required=True)


# FileListRemote = jsl.ArrayField(items=jsl.StringField(pattern=SchemaUtilPatterns.absPathPattern),
# min_items=1, unique_items=True, required=True)

# non-auto classes are usually input manually.
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
    site = jsl.DocumentField(FileTransferSiteLocalAuto, required=True)
    filelist = FileListRelative
