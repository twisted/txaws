'''Reactor utilities.'''

def get_exitcode_reactor():
    """
    This is only neccesary until a fix like the one outlined here is
    implemented for Twisted:
        http://twistedmatrix.com/trac/ticket/2182
    """
    from twisted.internet.main import installReactor
    from twisted.internet.selectreactor import SelectReactor

    class ExitCodeReactor(SelectReactor):

        def stop(self, exitStatus=0):
            super(ExitCodeReactor, self).stop()
            self.exitStatus = exitStatus

        def run(self, *args, **kwargs):
            super(ExitCodeReactor, self).run(*args, **kwargs)
            return self.exitStatus

    reactor = ExitCodeReactor()
    installReactor(reactor)
    return reactor


try:
    reactor = get_exitcode_reactor()
except:
    from twisted.internet import reactor
