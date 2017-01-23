# Licenced under the txaws licence available at /LICENSE in the txaws source.

"""
Basic functionality to aid in the definition of in-memory test doubles.
"""

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
        return oself._controller.get_state(oself.creds)



@attr.s
class MemoryClient(object):
    _state = ControllerState()

    _controller = attr.ib()
    creds = attr.ib()


@attr.s(frozen=True)
class MemoryService(object):
    """
    L{MemoryService} is the entrypoint into an in-memory implementation of a
    single AWS service.

    @ivar client_factory: A callable which returns the client object for this
        service.  Its arguments are this object, some credentials, and any
        extra arguments passed to ``client``.

    @ivar state_factory: A no-argument callable which returns the
        implementation state for a client object returned by
        C{client_factory}.
    """
    client_factory = attr.ib()
    state_factory = attr.ib()

    _state = attr.ib(
        default=attr.Factory(dict),
        init=False,
        hash=False,
    )

    def get_state(self, creds):
        """
        Get the state that belongs to a particular account.

        @param creds: The credentials which identify a particular account.
        @type creds: L{AWSCredentials}

        @return: The state for the account, creating it if necessary.  The
            state will be whatever C{state_factory} returns.
        """
        key = (creds.access_key, creds.secret_key)
        return self._state.setdefault(key, self.state_factory())

    def client(self, creds, *a, **kw):
        """
        Get an in-memory verified fake client for this service.

        @param creds: The credentials to associate with the account.  No
            authentication is performed but this identifies the state the
            client will find.
        @type creds: L{AWSCredentials}

        @return: A new client for this service along with the state object for
            the client.
        @rtype: L{tuple}
        """
        client = self.client_factory(self, creds, *a, **kw)
        return client, self.get_state(creds)
