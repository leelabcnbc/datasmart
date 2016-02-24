import sys
import os

global_config = {'project_root': os.path.abspath(sys.path[0]),
                 'root_package_spec': __name__}

assert os.sep == '/'  # now only Linux and Mac are supported, due to the separator.
