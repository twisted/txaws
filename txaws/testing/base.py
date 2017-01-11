import os
from weakref import WeakKeyDictionary

import attr

from twisted.trial.unittest import TestCase

class TXAWSTestCase(TestCase):
    """Support for isolation of txaws tests."""

    def setUp(self):
        TestCase.setUp(self)
        self._stash_environ()

    def _stash_environ(self):
        self.orig_environ = dict(os.environ)
        self.addCleanup(self._restore_environ)
        to_delete = [
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY",
            "AWS_ENDPOINT",
        ]
        for key in to_delete:
            if key in os.environ:
                del os.environ[key]

    def _restore_environ(self):
        os.environ.clear()
        os.environ.update(self.orig_environ)



class ControllerState(object):
    def __get__(self, oself, type):
        return oself._controller.get_state(oself)



@attr.s
class MemoryClient(object):
    _state = ControllerState()

    _controller = attr.ib()



@attr.s(frozen=True)
class MemoryService(object):
    clientFactory = attr.ib()
    stateFactory = attr.ib()

    _state = attr.ib(
        default=attr.Factory(dict),
        init=False,
        hash=False,
    )

    def get_state(self, creds):
        return self._state.setdefault(creds, self.stateFactory())

    def client(self, creds, *a, **kw):
        client = self.clientFactory(self, creds, *a, **kw)
        return client, self.get_state(creds)
