from bson import ObjectId
# this is a query template for downloading file. In the end, the `result` variable should be a dictionary
# of fields `site` and `filelist`, following format of `FileTransferSiteAndFileListAny` in datasmart.core.schemautil

# 1. query with time
query_doc_by_time = {}
# 2. query with note
query_doc_by_note = {}
# 3. query with _id
query_doc_by_id = {'_id': ObjectId('56dcfa5eaea6dc266cb124ae')}


query_doc = query_doc_by_id

# make sure there's only one such doc, ignoring vulnerable window.
doc_count = client_instance['demo']['file_upload'].count(query_doc)
assert doc_count==1, "there must be only one matching doc!"
doc = client_instance['demo']['file_upload'].find_one(query_doc)
result = doc['uploaded_files']