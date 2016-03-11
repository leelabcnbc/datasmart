from datasmart.actions.demo.file_upload import FileUploadAction

if __name__ == '__main__':
    a = FileUploadAction()
    test = input('enter to run, and enter anything then enter to revoke.')
    if not test:
        a.run()
    else:
        a.revoke()