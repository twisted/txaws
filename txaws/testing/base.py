import os

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


class _ControllerState(object):
    def __get__(self, oself, type):
        return oself._controller.get_state(oself)
