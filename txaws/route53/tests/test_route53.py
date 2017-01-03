
from twisted.web.static import Data
from twisted.web.resource import IResource, Resource
from twisted.internet.task import Cooperator

from txaws.service import AWSServiceRegion
from txaws.testing.base import TXAWSTestCase
from txaws.testing.memoryagent import MemoryAgent

from txaws.route53.client import (
    NS, SOA, CNAME, Name, get_route53_client,
    create_rrset, delete_rrset, upsert_rrset,
)

def uncooperator(started=True):
    return Cooperator(
        # Don't stop consuming the iterator.
        terminationPredicateFactory=lambda: lambda: False,
        scheduler=lambda what: (what(), object())[1],
        started=started,
    )

class POSTableData(Data):
    posted = ()

    def render_POST(self, request):
        self.posted += (request.content.read(),)
        return Data.render_GET(self, request)


def static_resource(hierarchy):
    root = Resource()
    for k, v in hierarchy.iteritems():
        if IResource.providedBy(v):
            root.putChild(k, v)
        elif isinstance(v, dict):
            root.putChild(k, static_resource(v))
        else:
            raise NotImplementedError(v)
    return root


class sample_list_resource_record_sets_result(object):
    name = u"example.invalid."
    soa = SOA(
        mname=Name(u"1.awsdns-1.net."),
        rname=Name(u"awsdns-hostmaster.amazon.com."),
        serial=1,
        refresh=7200,
        retry=900,
        expire=1209600,
        minimum=86400,
    )
    ns1 = NS(
        nameserver=Name(u"ns-1.awsdns-1.net."),
    )
    ns2 = NS(
        nameserver=Name(u"ns-2.awsdns-2.net."),
    )

    # The existence of a CNAME record for example.invalid. is bogus
    # because if you have a CNAME record for a name you're not
    # supposed to have any other records for it - and we have soa, ns,
    # etc.  However, noone is interpreting this data with DNS
    # semantics.  We're just parsing it.  Hope that's okay with you.
    cname = CNAME(
        canonical_name=Name(u"somewhere.example.invalid."),
    )
    xml = u"""\
<?xml version="1.0"?>
<ListResourceRecordSetsResponse xmlns="https://route53.amazonaws.com/doc/2013-04-01/"><ResourceRecordSets><ResourceRecordSet><Name>{name}</Name><Type>NS</Type><TTL>172800</TTL><ResourceRecords><ResourceRecord><Value>{ns1.nameserver}</Value></ResourceRecord><ResourceRecord><Value>{ns2.nameserver}</Value></ResourceRecord></ResourceRecords></ResourceRecordSet><ResourceRecordSet><Name>{name}</Name><Type>SOA</Type><TTL>900</TTL><ResourceRecords><ResourceRecord><Value>{soa.mname} {soa.rname} {soa.serial} {soa.refresh} {soa.retry} {soa.expire} {soa.minimum}</Value></ResourceRecord></ResourceRecords></ResourceRecordSet><ResourceRecordSet><Name>{name}</Name><Type>CNAME</Type><TTL>1800</TTL><ResourceRecords><ResourceRecord><Value>{cname.canonical_name}</Value></ResourceRecord></ResourceRecords></ResourceRecordSet></ResourceRecordSets><IsTruncated>false</IsTruncated><MaxItems>100</MaxItems></ListResourceRecordSetsResponse>
""".format(name=name, soa=soa, ns1=ns1, ns2=ns2, cname=cname).encode("utf-8")


class sample_change_resource_record_sets_result(object):
    name = u"example.invalid."
    create_type = u"NS"
    create_rrset = [NS(Name(u"ns1.example.invalid.")), NS(Name(u"ns2.example.invalid."))]

    xml = b"""\
<?xml version="1.0" encoding="UTF-8"?>
<ChangeResourceRecordSetsResponse>
   <ChangeInfo>
      <Comment>string</Comment>
      <Id>string</Id>
      <Status>string</Status>
      <SubmittedAt>timestamp</SubmittedAt>
   </ChangeInfo>
</ChangeResourceRecordSetsResponse>
"""

class sample_list_hosted_zones_result(object):
    details = dict(
        name=u"example.invalid.",
        identifier=u"/hostedzone/ABCDEF123456",
        reference=u"3CCF1549-806D-F91A-906F-A3727E910C87",
        count=6,
    )
    xml = u"""\
<?xml version="1.0"?>
<ListHostedZonesResponse xmlns="https://route53.amazonaws.com/doc/2013-04-01/"><HostedZones><HostedZone><Id>{identifier}</Id><Name>{name}</Name><CallerReference>{reference}</CallerReference><Config><PrivateZone>false</PrivateZone></Config><ResourceRecordSetCount>{count}</ResourceRecordSetCount></HostedZone></HostedZones><IsTruncated>false</IsTruncated><MaxItems>100</MaxItems></ListHostedZonesResponse>
""".format(**details).encode("utf-8")
    

class ListHostedZonesTestCase(TXAWSTestCase):
    """
    Tests for C{list_hosted_zones}.
    """
    def test_some_zones(self):
        agent = MemoryAgent(static_resource({
            b"2013-04-01": {
                b"hostedzone": Data(
                    sample_list_hosted_zones_result.xml,
                    b"text/xml",
                ),
            },
        }))
        aws = AWSServiceRegion(access_key="abc", secret_key="def")
        client = get_route53_client(agent, aws, uncooperator())
        zones = self.successResultOf(client.list_hosted_zones())
        expected = [sample_list_hosted_zones_result.details]
        self.assertEquals(expected, zones)


class ListResourceRecordSetsTestCase(TXAWSTestCase):
    """
    Tests for C{list_resource_record_sets}.
    """
    def test_some_records(self):
        zone_id = b"ABCDEF1234"
        agent = MemoryAgent(static_resource({
            b"2013-04-01": {
                b"hostedzone": {
                    zone_id: {
                        b"rrset": Data(
                            sample_list_resource_record_sets_result.xml,
                            b"text/xml",
                        )
                    }
                }
            }
        }))
        aws = AWSServiceRegion(access_key="abc", secret_key="def")
        client = get_route53_client(agent, aws, uncooperator())
        rrsets = self.successResultOf(client.list_resource_record_sets(
            zone_id=zone_id,
        ))
        expected = {
            Name(sample_list_resource_record_sets_result.name): {
                sample_list_resource_record_sets_result.soa,
                sample_list_resource_record_sets_result.ns1,
                sample_list_resource_record_sets_result.ns2,
                sample_list_resource_record_sets_result.cname,
            }
        }
        self.assertEquals(rrsets, expected)


class ChangeResourceRecordSetsTestCase(TXAWSTestCase):
    """
    Tests for C{change_resource_record_sets}.
    """
    def test_some_changes(self):
        change_resource = POSTableData(
            sample_change_resource_record_sets_result.xml,
            b"text/xml",
        )
        zone_id = b"ABCDEF1234"
        agent = MemoryAgent(static_resource({
            b"2013-04-01": {
                b"hostedzone": {
                    zone_id: {
                        b"rrset": change_resource,
                    }
                },
            },
        }))
        aws = AWSServiceRegion(access_key="abc", secret_key="def")
        client = get_route53_client(agent, aws, uncooperator())
        self.successResultOf(client.change_resource_record_sets(
            zone_id=zone_id,
            changes=[
                create_rrset(
                    sample_change_resource_record_sets_result.name,
                    sample_change_resource_record_sets_result.create_type,
                    sample_change_resource_record_sets_result.create_rrset,
                ),
                # delete_rrset(
                #     sample_change_resource_record_sets_result.name,
                #     sample_change_resource_record_sets_result.delete_type,
                #     sample_change_resource_record_sets_result.delete_rrset,
                # ),
                # upsert_rrset(
                #     sample_change_resource_record_sets_result.name,
                #     sample_change_resource_record_sets_result.upsert_type,
                #     sample_change_resource_record_sets_result.upsert_rrset,
                # ),
            ],
        ))
        # Ack, what a pathetic assertion.
        expected = b"""\
<?xml version="1.0" encoding="UTF-8"?>
<ChangeResourceRecordSetsRequest xmlns="https://route53.amazonaws.com/doc/2013-04-01/"><ChangeBatch><Changes><Change><Action>CREATE</Action><ResourceRecordSet><Name>example.invalid.</Name><Type>NS</Type><TTL>86400</TTL><ResourceRecords><ResourceRecord><Value>ns1.example.invalid.</Value></ResourceRecord><ResourceRecord><Value>ns2.example.invalid.</Value></ResourceRecord></ResourceRecords></ResourceRecordSet></Change></Changes></ChangeBatch></ChangeResourceRecordSetsRequest>"""
        self.assertEqual((expected,), change_resource.posted)
