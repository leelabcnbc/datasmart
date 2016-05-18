from datasmart.actions.klab.mouse_exp import MouseExpAction

if __name__ == '__main__':
    a = MouseExpAction()
    test = input('enter to run, and enter anything then enter to revoke.')
    if not test:
        a.run()
    else:
        a.revoke()
