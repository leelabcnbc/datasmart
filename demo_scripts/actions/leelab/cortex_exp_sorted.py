from datasmart.actions.leelab.cortex_exp_sorted import CortexExpSortedAction

if __name__ == '__main__':
    a = CortexExpSortedAction()
    test = input('enter to run, and enter anything then enter to revoke.')
    if not test:
        a.run()
    else:
        a.revoke()
