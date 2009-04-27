# Copyright (C) 2009 Robert Collins <robertc@robertcollins.net>
# Licenced under the txaws licence available at /LICENSE in the txaws source.

"""A GTK client for working with aws."""

from __future__ import absolute_import

__all__ = ['main']

import gtk

class AWSStatusIcon(gtk.StatusIcon):
    """A status icon shown when instances are running."""

    def __init__(self, reactor):
        gtk.StatusIcon.__init__(self)
        self.set_tooltip('AWS Status - ? instances')
        self.set_from_stock(gtk.STOCK_NETWORK)
        self.set_visible(True)
        self.reactor = reactor
        self.connect('activate', self.on_activate)
        self.probing = False
        # Nested import because otherwise we get 'reactor already installed'.
        from txaws.ec2.client import EC2Client
        self.client = EC2Client()
        self.on_activate(None)

    def on_activate(self, data):
        if self.probing:
            # don't ask multiple times.
            return
        self.probing = True
        self.client.describe_instances().addCallbacks(self.showhide, self.errorit)

    def showhide(self, reservation):
        if len(reservation) == 0:
            self.set_visible(False)
        else:
            self.set_visible(True)
        self.queue_check()

    def queue_check(self):
        self.probing = False
        self.reactor.callLater(60, self.on_activate, None)

    def errorit(self, error):
        # debugging output for now.
        print error.value, error.value.response
        self.queue_check()


def main(argv, reactor=None):
    """Run the client GUI.

    Typical use:
    >>> sys.exit(main(sys.argv))

    :param argv: The arguments to run it with, e.g. sys.argv.
    :param reactor: The reactor to use. Must be compatible with gtk as this
        module uses gtk API's.
    :return exitcode: The exit code it returned, as per sys.exit.
    """
    if reactor is None:
        from twisted.internet import gtk2reactor
        gtk2reactor.install()
        from twisted.internet import reactor
    status = AWSStatusIcon(reactor)
    reactor.run()
