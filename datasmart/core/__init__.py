import sys
import os


global_config = {'project_root': os.path.abspath(sys.path[0]),
                 'root_package_spec': __name__[:-5]}

assert os.sep == '/'  # now only Linux and Mac are supported, due to the separator.
keywords = ('_data',
            # the default local data folder for file transfer.
            # This is just a guess, since FileTransfer doesn't create the folder until initialization.
            'default_local_site', # default local site folder for file transfer. Again, this is a guess.
            'query_template.py',  # the query template file
            'prepare_result.p',  # the prepared result.
            )
