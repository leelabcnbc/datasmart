class StringPatterns:
    sha1Pattern = "^[0-9a-f]{40}$"  # only allow lowercase to be more strict.
    absPathPattern = '(^(/[^/]+)+$)|(^/$)'
    relativePathPattern = '^([^/]+)(/[^/]+)*$'
    absOrRelativePathPattern = '(' + absPathPattern + ')' + '|' + '(' + relativePathPattern + ')'
    absOrRelativePathPatternOrEmpty = absOrRelativePathPattern + '|(^$)'
    strictFilenameLowerPattern = lambda ext: "^[0-9a-z_\\-]+\\.{}$".format(ext)
    bsonObjectIdPattern = "^[0-9a-f]{24}$"  # only allow lowercase to be more strict.
