
from twisted.web.static import Data
from twisted.web.resource import IResource, Resource
from twisted.internet.task import Cooperator

from txaws.service import AWSServiceRegion
from txaws.testing.integration import get_live_service
from txaws.testing.base import TXAWSTestCase
from txaws.testing.route53_tests import route53_integration_tests

from txaws.route53.model import (
    HostedZone, RRSetKey, RRSet, AliasRRSet,
    create_rrset, delete_rrset, upsert_rrset,
)
from txaws.route53.client import (
    NS, SOA, CNAME, Name, get_route53_client,
)

from treq.testing import RequestTraversalAgent

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
    label = Name(u"example.invalid.")
    soa_ttl = 60
    soa = SOA(
        mname=Name(u"1.awsdns-1.net."),
        rname=Name(u"awsdns-hostmaster.amazon.com."),
        serial=1,
        refresh=7200,
        retry=900,
        expire=1209600,
        minimum=86400,
    )
    ns_ttl = 120
    ns1 = NS(
        nameserver=Name(u"ns-1.awsdns-1.net."),
    )
    ns2 = NS(
        nameserver=Name(u"ns-2.awsdns-2.net."),
    )

    cname_ttl = 180
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
<ListResourceRecordSetsResponse xmlns="https://route53.amazonaws.com/doc/2013-04-01/"><ResourceRecordSets><ResourceRecordSet><Name>{label}</Name><Type>NS</Type><TTL>{ns_ttl}</TTL><ResourceRecords><ResourceRecord><Value>{ns1.nameserver}</Value></ResourceRecord><ResourceRecord><Value>{ns2.nameserver}</Value></ResourceRecord></ResourceRecords></ResourceRecordSet><ResourceRecordSet><Name>{label}</Name><Type>SOA</Type><TTL>{soa_ttl}</TTL><ResourceRecords><ResourceRecord><Value>{soa.mname} {soa.rname} {soa.serial} {soa.refresh} {soa.retry} {soa.expire} {soa.minimum}</Value></ResourceRecord></ResourceRecords></ResourceRecordSet><ResourceRecordSet><Name>{label}</Name><Type>CNAME</Type><TTL>{cname_ttl}</TTL><ResourceRecords><ResourceRecord><Value>{cname.canonical_name}</Value></ResourceRecord></ResourceRecords></ResourceRecordSet></ResourceRecordSets><IsTruncated>false</IsTruncated><MaxItems>100</MaxItems></ListResourceRecordSetsResponse>
""".format(
    label=label,
    soa=soa, soa_ttl=soa_ttl,
    ns1=ns1, ns2=ns2, ns_ttl=ns_ttl,
    cname=cname, cname_ttl=cname_ttl,
).encode("utf-8")


class sample_change_resource_record_sets_result(object):
    rrset = RRSet(
        label=Name(u"example.invalid."),
        type=u"NS",
        ttl=86400,
        records={
            NS(Name(u"ns1.example.invalid.")),
            NS(Name(u"ns2.example.invalid.")),
        },
    )
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
        identifier=u"ABCDEF123456",
        reference=u"3CCF1549-806D-F91A-906F-A3727E910C87",
        rrset_count=6,
    )
    xml = u"""\
<?xml version="1.0"?>
<ListHostedZonesResponse xmlns="https://route53.amazonaws.com/doc/2013-04-01/"><HostedZones><HostedZone><Id>/hostedzone/{identifier}</Id><Name>{name}</Name><CallerReference>{reference}</CallerReference><Config><PrivateZone>false</PrivateZone></Config><ResourceRecordSetCount>{rrset_count}</ResourceRecordSetCount></HostedZone></HostedZones><IsTruncated>false</IsTruncated><MaxItems>100</MaxItems></ListHostedZonesResponse>
""".format(**details).encode("utf-8")


class sample_list_resource_records_with_alias_result(object):
    normal_target = Name(u"bar.example.invalid.")
    normal = RRSet(
        label=Name(u"foo.example.invalid."),
        type=u"CNAME",
        ttl=60,
        records={CNAME(canonical_name=normal_target)},
    )

    normal_xml = u"""\
<ResourceRecordSet><Name>{label}</Name><Type>{type}</Type><TTL>{ttl}</TTL><ResourceRecords><ResourceRecord><Value>{value}</Value></ResourceRecord></ResourceRecords></ResourceRecordSet>
""".format(
    label=normal.label,
    type=normal.type,
    ttl=normal.ttl,
    value=normal_target,
)

    alias = AliasRRSet(
        label=Name(u"bar.example.invalid."),
        type=u"A",
        dns_name=Name(
            u"dualstack.a952f315901e6b3c812e57076f5b4138-0795221525.us-east-1.elb.amazonaws.com.",
        ),
        evaluate_target_health=False,
        hosted_zone_id=u"ZSXD5Q7O3X7TRK",
    )

    alias_xml = u"""\
<ResourceRecordSet><Name>{label}</Name><Type>{type}</Type><AliasTarget><HostedZoneId>{hosted_zone_id}</HostedZoneId><DNSName>{dns_name}</DNSName><EvaluateTargetHealth>{evaluate_target_health}</EvaluateTargetHealth></AliasTarget></ResourceRecordSet>
""".format(
    label=alias.label,
    type=alias.type,
    hosted_zone_id=alias.hosted_zone_id,
    dns_name=alias.dns_name,
    evaluate_target_health=[u"false", u"true"][alias.evaluate_target_health],
)

    xml = u"""\
<?xml version="1.0"?>\n
<ListResourceRecordSetsResponse xmlns="https://route53.amazonaws.com/doc/2013-04-01/"><ResourceRecordSets>{normal}{alias}</ResourceRecordSets><IsTruncated>false</IsTruncated><MaxItems>100</MaxItems></ListResourceRecordSetsResponse>
""".format(normal=normal_xml, alias=alias_xml).encode("utf-8")


class ListHostedZonesTestCase(TXAWSTestCase):
    """
    Tests for C{list_hosted_zones}.
    """
    def test_some_zones(self):
        agent = RequestTraversalAgent(static_resource({
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
        expected = [HostedZone(**sample_list_hosted_zones_result.details)]
        self.assertEquals(expected, zones)


class ListResourceRecordSetsTestCase(TXAWSTestCase):
    """
    Tests for C{list_resource_record_sets}.
    """
    def _client_for_rrsets(self, zone_id, rrsets_xml):
        agent = RequestTraversalAgent(static_resource({
            b"2013-04-01": {
                b"hostedzone": {
                    zone_id: {
                        b"rrset": Data(
                            rrsets_xml,
                            b"text/xml",
                        )
                    }
                }
            }
        }))
        aws = AWSServiceRegion(access_key="abc", secret_key="def")
        return get_route53_client(agent, aws, uncooperator())


    def test_some_records(self):
        zone_id = b"ABCDEF1234"
        client = self._client_for_rrsets(
            zone_id, sample_list_resource_record_sets_result.xml,
        )
        rrsets = self.successResultOf(client.list_resource_record_sets(
            zone_id=zone_id,
        ))
        expected = {
            RRSetKey(
                label=sample_list_resource_record_sets_result.label,
                type=u"SOA",
            ): RRSet(
                label=sample_list_resource_record_sets_result.label,
                type=u"SOA",
                ttl=sample_list_resource_record_sets_result.soa_ttl,
                records={sample_list_resource_record_sets_result.soa},
            ),
            RRSetKey(
                label=sample_list_resource_record_sets_result.label,
                type=u"NS",
            ): RRSet(
                label=sample_list_resource_record_sets_result.label,
                type=u"NS",
                ttl=sample_list_resource_record_sets_result.ns_ttl,
                records={
                    sample_list_resource_record_sets_result.ns1,
                    sample_list_resource_record_sets_result.ns2,
                },
            ),
            RRSetKey(
                label=sample_list_resource_record_sets_result.label,
                type=u"CNAME",
            ): RRSet(
                label=sample_list_resource_record_sets_result.label,
                type=u"CNAME",
                ttl=sample_list_resource_record_sets_result.cname_ttl,
                records={sample_list_resource_record_sets_result.cname},
            ),
        }
        self.assertEquals(rrsets, expected)


    def test_alias_records(self):
        """
        If there are special AWS-custom "alias" records in the response, they are
        represented in the result as ``AliasRRSet`` instances.
        """
        zone_id = b"ABCDEF1234"
        client = self._client_for_rrsets(
            zone_id, sample_list_resource_records_with_alias_result.xml,
        )
        rrsets = self.successResultOf(client.list_resource_record_sets(
            zone_id=zone_id,
        ))
        expected = {
            RRSetKey(
                label=sample_list_resource_records_with_alias_result.normal.label,
                type=sample_list_resource_records_with_alias_result.normal.type,
            ): sample_list_resource_records_with_alias_result.normal,
            RRSetKey(
                label=sample_list_resource_records_with_alias_result.alias.label,
                type=sample_list_resource_records_with_alias_result.alias.type,
            ): sample_list_resource_records_with_alias_result.alias,
        }
        self.assertEquals(rrsets, expected)


    def test_unsupported_records(self):
        """
        If there are resource record sets of unsupported type in the response,
        they are dropped.
        """
        zone_id = b"ABCDEF1234"
        crazy_xml = sample_list_resource_records_with_alias_result.xml.replace(
            b"ResourceRecords>", b"XXResourceRecords>",
        ).replace(
            b"AliasTarget>", b"XXAliasTarget>"
        )
        client = self._client_for_rrsets(zone_id, crazy_xml)
        rrsets = self.successResultOf(client.list_resource_record_sets(
            zone_id=zone_id,
        ))
        expected = {}
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
        zone_id = u"ABCDEF1234"
        agent = RequestTraversalAgent(static_resource({
            b"2013-04-01": {
                b"hostedzone": {
                    zone_id.encode("ascii"): {
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
                create_rrset(sample_change_resource_record_sets_result.rrset),
                delete_rrset(sample_change_resource_record_sets_result.rrset),
                upsert_rrset(sample_change_resource_record_sets_result.rrset),
            ],
        ))
        # Ack, what a pathetic assertion.
        change_template = u"<Change><Action>{action}</Action><ResourceRecordSet><Name>example.invalid.</Name><Type>NS</Type><TTL>86400</TTL><ResourceRecords><ResourceRecord><Value>ns1.example.invalid.</Value></ResourceRecord><ResourceRecord><Value>ns2.example.invalid.</Value></ResourceRecord></ResourceRecords></ResourceRecordSet></Change>"
        changes = [
            change_template.format(action=u"CREATE"),
            change_template.format(action=u"DELETE"),
            change_template.format(action=u"UPSERT"),
        ]
        expected = u"""\
<?xml version="1.0" encoding="UTF-8"?>
<ChangeResourceRecordSetsRequest xmlns="https://route53.amazonaws.com/doc/2013-04-01/"><ChangeBatch><Changes>{changes}</Changes></ChangeBatch></ChangeResourceRecordSetsRequest>""".format(changes=u"".join(changes)).encode("utf-8")
        self.assertEqual((expected,), change_resource.posted)



def get_live_client(case):
    return get_live_service(case).get_route53_client()


class LiveRoute53TestCase(route53_integration_tests(get_live_client)):
    """
    Tests for the real Route53 implementation against AWS itself.
    """
