import jsl
from .stringpatterns import StringPatterns

class GitRepoRef(jsl.Document):
    repo_url = jsl.StringField(format="uri", required=True)
    repo_hash = jsl.StringField(pattern=StringPatterns.sha1Pattern, required=True)