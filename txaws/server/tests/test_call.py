from twisted.trial.unittest import TestCase

from txaws.server.call import Call


class CallTest(TestCase):

    def test_default_version(self):
        """
        If no version is explicitly requested, C{version} is set to
        2008-12-01, which is the earliest version we support.
        """
        call = Call()
        self.assertEqual(call.version, "2008-12-01")
