from datasmart.actions.demo.file_download import FileDownloadAction

if __name__ == '__main__':
    a = FileDownloadAction()
    test = input('enter to run, and enter anything then enter to exit.')
    if not test:
        a.run()