# Licenced under the txaws licence available at /LICENSE in the txaws source.

"""
Tests for L{txaws.route53.model}.
"""

from ipaddress import IPv4Address

from txaws.util import XML
from txaws.testing.base import TXAWSTestCase

from txaws.route53.model import (
    Name, SOA, NS, CNAME, A,
)

class BasicResourceRecordTestCase(TXAWSTestCase):
    """
    Tests for L{IBasicResourceRecord} model objects.
    """
    def _test_roundtrip(self, loader, expected, element):
        """
        Verify that C{loader} loads C{element} to C{expected} and C{expected}
        serializes itself to the value of C{element}.
        """
        actual = loader.basic_from_element(element)
        self.assertEqual(expected, actual)
        self.assertEqual(
            element.find("Value").text,
            expected.to_text(),
        )

    _soa_xml = (
        "<ResourceRecord>"
        "<Value>"
        "ns-857.example.invalid. awsdns-hostmaster.example.invalid. "
        "1 7200 900 1209600 86400"
        "</Value>"
        "</ResourceRecord>"
    )
    def test_soa(self):
        """
        L{SOA} can round-trip an I{SOA} record through XML.
        """
        self._test_roundtrip(
            SOA,
            SOA(
                mname=Name(u"ns-857.example.invalid."),
                rname=Name(u"awsdns-hostmaster.example.invalid."),
                serial=1,
                refresh=7200,
                retry=900,
                expire=1209600,
                minimum=86400,
            ),
            XML(self._soa_xml),
        )

    _ns_xml = (
        "<ResourceRecord>"
        "<Value>"
        "ns1.example.invalid."
        "</Value>"
        "</ResourceRecord>"
    )
    def test_ns(self):
        """
        L{NS} can round-trip an I{NS} record through XML.
        """
        self._test_roundtrip(
            NS,
            NS(nameserver=Name(u"ns1.example.invalid.")),
            XML(self._ns_xml),
        )

    _cname_xml = (
        "<ResourceRecord>"
        "<Value>"
        "sub.example.invalid."
        "</Value>"
        "</ResourceRecord>"
    )
    def test_cname(self):
        """
        L{CNAME} can round-trip a I{CNAME} record through XML.
        """
        self._test_roundtrip(
            CNAME,
            CNAME(canonical_name=Name(u"sub.example.invalid.")),
            XML(self._cname_xml),
        )

    _a_xml = (
        "<ResourceRecord>"
        "<Value>"
        "1.2.3.4"
        "</Value>"
        "</ResourceRecord>"
    )
    def test_a(self):
        """
        L{A} can round-trip an I{A} record through XML.
        """
        self._test_roundtrip(
            A,
            A(address=IPv4Address(u"1.2.3.4")),
            XML(self._a_xml),
        )
