from twisted.trial.unittest import TestCase

from txaws.s3 import acls


class ACLTests(TestCase):

    def test_owner_to_xml(self):
        owner = acls.Owner(id='8a6925ce4adf588a4f21c32aa379004fef',
                           display_name='BucketOwnersEmail@amazon.com')
        xml_bytes = owner.to_xml()
        self.assertEquals(xml_bytes, """\
<Owner>
  <ID>8a6925ce4adf588a4f21c32aa379004fef</ID>
  <DisplayName>BucketOwnersEmail@amazon.com</DisplayName>
</Owner>
""")


    def test_grantee_to_xml(self):
        grantee = acls.Grantee(id='8a6925ce4adf588a4f21c32aa379004fef',
                               display_name='BucketOwnersEmail@amazon.com')
        xml_bytes = grantee.to_xml()
        self.assertEquals(xml_bytes, """\
<Grantee xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:type="CanonicalUser">
  <ID>8a6925ce4adf588a4f21c32aa379004fef</ID>
  <DisplayName>BucketOwnersEmail@amazon.com</DisplayName>
</Grantee>
""")


    def test_grant_to_xml(self):
        grantee = acls.Grantee(id='8a6925ce4adf588a4f21c32aa379004fef',
                               display_name='BucketOwnersEmail@amazon.com')
        grant = acls.Grant(grantee, 'FULL_CONTROL')
        xml_bytes = grant.to_xml()
        self.assertEquals(xml_bytes, """\
<Grant>
  <Grantee xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:type="CanonicalUser">
    <ID>8a6925ce4adf588a4f21c32aa379004fef</ID>
    <DisplayName>BucketOwnersEmail@amazon.com</DisplayName>
  </Grantee>
  <Permission>FULL_CONTROL</Permission>
</Grant>
""")

    def test_access_control_policy_to_xml(self):
        
        grantee = acls.Grantee(id='8a6925ce4adf588a4f21c32aa379004fef',
                               display_name='foo@example.net')
        grant1 = acls.Grant(grantee, 'FULL_CONTROL')
        grantee = acls.Grantee(id='8a6925ce4adf588a4f21c32aa37900feed',
                               display_name='bar@example.net')
        grant2 = acls.Grant(grantee, 'READ')
        owner = acls.Owner(id='8a6925ce4adf588a4f21c32aa37900beef',
                           display_name='baz@example.net')
        acp = acls.AccessControlPolicy(owner=owner, access_control_list=[grant1, grant2])
        xml_bytes = acp.to_xml()
        self.assertEquals(xml_bytes, """\
<AccessControlPolicy>
  <Owner>
    <ID>8a6925ce4adf588a4f21c32aa37900beef</ID>
    <DisplayName>baz@example.net</DisplayName>
  </Owner>
  <AccessControlList>
    <Grant>
      <Grantee xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:type="CanonicalUser">
        <ID>8a6925ce4adf588a4f21c32aa379004fef</ID>
        <DisplayName>foo@example.net</DisplayName>
      </Grantee>
      <Permission>FULL_CONTROL</Permission>
    </Grant>
    <Grant>
      <Grantee xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:type="CanonicalUser">
        <ID>8a6925ce4adf588a4f21c32aa37900feed</ID>
        <DisplayName>bar@example.net</DisplayName>
      </Grantee>
      <Permission>READ</Permission>
    </Grant>
  </AccessControlList>
</AccessControlPolicy>""") 


    def test_permission_enum(self):
        grantee = acls.Grantee(id='8a6925ce4adf588a4f21c32aa379004fef',
                               display_name='BucketOwnersEmail@amazon.com')
        acls.Grant(grantee, 'FULL_CONTROL')
        acls.Grant(grantee, 'WRITE')
        acls.Grant(grantee, 'WRITE_ACP')
        acls.Grant(grantee, 'READ')
        acls.Grant(grantee, 'READ_ACP')
        self.assertRaises(ValueError, acls.Grant, grantee, 'GO_HOG_WILD')

