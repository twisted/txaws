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
        if "AWS_ACCESS_KEY_ID" in os.environ:
            del os.environ["AWS_ACCESS_KEY_ID"]
        if "AWS_SECRET_ACCESS_KEY" in os.environ:
            del os.environ["AWS_SECRET_ACCESS_KEY"]
        if "AWS_ENDPOINT" in os.environ:
            del os.environ["AWS_ENDPOINT"]

    def _restore_environ(self):
        for key in set(os.environ) - set(self.orig_environ):
            del os.environ[key]
        os.environ.update(self.orig_environ)

