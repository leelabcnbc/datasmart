from datasmart.core import schemautil

if __name__ == '__main__':
    FileTransferSiteAndFileListLocal = schemautil.FileTransferSiteAndFileListRemote
    print(schemautil.get_schema_string(FileTransferSiteAndFileListLocal))