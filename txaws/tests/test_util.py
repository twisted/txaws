from urlparse import urlparse

from twisted.trial.unittest import TestCase

from txaws.util import hmac_sha1, iso8601time, parse

class MiscellaneousTests(TestCase):

    def test_hmac_sha1(self):
        cases = [
            ("0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b".decode("hex"),
             "Hi There", "thcxhlUFcmTii8C2+zeMjvFGvgA="),
            ("Jefe", "what do ya want for nothing?",
             "7/zfauXrL6LSdBbV8YTfnCWafHk="),
            ("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa".decode("hex"),
             "\xdd" * 50, "El1zQrmsEc2Ro5r0iqF7T2PxddM="),
            ]

        for key, data, expected in cases:
            self.assertEqual(hmac_sha1(key, data), expected)

    def test_iso8601time(self):
        self.assertEqual("2006-07-07T15:04:56Z", iso8601time((2006,7,7,15,4,56,
            0, 0, 0)))


class ParseUrlTestCase(TestCase):
    """
    Test URL parsing facility and defaults values.
    """
    def test_parse(self):
        """
        L{parse} correctly parses a URL into its various components.
        """
        # The default port for HTTP is 80.
        self.assertEqual(
            parse("http://127.0.0.1/"),
            ("http", "127.0.0.1", 80, "/"))

        # The default port for HTTPS is 443.
        self.assertEqual(
            parse("https://127.0.0.1/"),
            ("https", "127.0.0.1", 443, "/"))

        # Specifying a port.
        self.assertEqual(
            parse("http://spam:12345/"),
            ("http", "spam", 12345, "/"))

        # Weird (but commonly accepted) structure uses default port.
        self.assertEqual(
            parse("http://spam:/"),
            ("http", "spam", 80, "/"))

        # Spaces in the hostname are trimmed, the default path is /.
        self.assertEqual(
            parse("http://foo "),
            ("http", "foo", 80, "/"))

    def test_externalUnicodeInterference(self):
        """
        L{parse} should return C{str} for the scheme, host, and path
        elements of its return tuple, even when passed an URL which has
        previously been passed to L{urlparse} as a C{unicode} string.
        """
        badInput = u"http://example1.com/path"
        goodInput = badInput.encode("ascii")
        urlparse(badInput)
        scheme, host, port, path = parse(goodInput)
        self.assertTrue(isinstance(scheme, str))
        self.assertTrue(isinstance(host, str))
        self.assertTrue(isinstance(path, str))
