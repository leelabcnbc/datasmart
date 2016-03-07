from actions.cortex_exp import CortexExpAction

if __name__ == '__main__':
    a = CortexExpAction()
    test = input('enter to run, and enter anything then enter to revoke.')
    if not test:
        a.run()
    else:
        a.clear_results()
