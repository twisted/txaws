# Licenced under the txaws licence available at /LICENSE in the txaws source.

"""
Tests for L{txaws.route53._util}.
"""

from txaws.testing.base import TXAWSTestCase

from txaws.route53._util import maybe_bytes_to_unicode, to_xml, tags


class MaybeBytesToUnicodeTestCase(TXAWSTestCase):
    """
    Tests for L{maybe_bytes_to_unicode}.
    """
    def test_bytes(self):
        """
        When called with an instance of L{bytes}, L{maybe_bytes_to_unicode}
        decodes its input using I{ascii} and returns the resulting unicode
        string as an instance of L{unicode}.
        """
        self.assertRaises(
            UnicodeDecodeError,
            lambda: maybe_bytes_to_unicode(u"\N{SNOWMAN}".encode("utf-8")),
        )
        decoded = maybe_bytes_to_unicode(b"hello world")
        self.assertIsInstance(decoded, unicode)
        self.assertEqual(decoded, u"hello world")

    def test_unicode(self):
        """
        When called with an instance of L{unicode},
        L{maybe_bytes_to_unicode} returns its input unmodified.
        """
        self.assertEqual(
            u"\N{SNOWMAN}",
            maybe_bytes_to_unicode(u"\N{SNOWMAN}"),
        )


class ToXMLTestCase(TXAWSTestCase):
    """
    Tests for L{to_xml}.
    """
    def test_none(self):
        """
        When called with L{None}, L{to_xml} returns a L{Deferred} that
        fires with C{b""}.
        """
        self.assertEqual(b"", self.successResultOf(to_xml(None)))


    def test_something(self):
        """
        When called with an instance of L{txaws.route53._util.Tag},
        L{to_xml} returns a L{Defered} giving the result of flattening
        it as an instance of L{bytes} with an xml doctype prepended.
        """
        self.assertEqual(
            """<?xml version="1.0" encoding="UTF-8"?>\n<Foo>bar</Foo>""",
            self.successResultOf(to_xml(tags.Foo(u"bar"))),
        )
