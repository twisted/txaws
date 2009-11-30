from txaws.version import aws_api


sample_required_describe_instances_result = """\
<?xml version="1.0"?>
<DescribeInstancesResponse xmlns="http://ec2.amazonaws.com/doc/%s/">
  <requestId>52b4c730-f29f-498d-94c1-91efb75994cc</requestId>
  <reservationSet>
    <item>
      <reservationId>r-cf24b1a6</reservationId>
      <ownerId>123456789012</ownerId>
      <groupSet>
        <item>
          <groupId>default</groupId>
        </item>
      </groupSet>
      <instancesSet>
        <item>
          <instanceId>i-abcdef01</instanceId>
          <imageId>ami-12345678</imageId>
          <instanceState>
            <code>16</code>
            <name>running</name>
          </instanceState>
          <privateDnsName>domU-12-31-39-03-15-11.compute-1.internal</privateDnsName>
          <dnsName>ec2-75-101-245-65.compute-1.amazonaws.com</dnsName>
          <instanceType>c1.xlarge</instanceType>
          <launchTime>2009-04-27T02:23:18.000Z</launchTime>
          <placement>
            <availabilityZone>us-east-1c</availabilityZone>
          </placement>
        </item>
      </instancesSet>
    </item>
  </reservationSet>
</DescribeInstancesResponse>
""" % (aws_api,)


sample_describe_instances_result = """\
<?xml version="1.0"?>
<DescribeInstancesResponse xmlns="http://ec2.amazonaws.com/doc/%s/">
  <requestId>52b4c730-f29f-498d-94c1-91efb75994cc</requestId>
  <reservationSet>
    <item>
      <reservationId>r-cf24b1a6</reservationId>
      <ownerId>123456789012</ownerId>
      <groupSet>
        <item>
          <groupId>default</groupId>
        </item>
      </groupSet>
      <instancesSet>
        <item>
          <instanceId>i-abcdef01</instanceId>
          <imageId>ami-12345678</imageId>
          <instanceState>
            <code>16</code>
            <name>running</name>
          </instanceState>
          <privateDnsName>domU-12-31-39-03-15-11.compute-1.internal</privateDnsName>
          <dnsName>ec2-75-101-245-65.compute-1.amazonaws.com</dnsName>
          <reason/>
          <keyName>keyname</keyName>
          <amiLaunchIndex>0</amiLaunchIndex>
          <productCodes>
            <productCode>774F4FF8</productCode>
          </productCodes>
          <instanceType>c1.xlarge</instanceType>
          <launchTime>2009-04-27T02:23:18.000Z</launchTime>
          <placement>
            <availabilityZone>us-east-1c</availabilityZone>
          </placement>
          <kernelId>aki-b51cf9dc</kernelId>
          <ramdiskId>ari-b31cf9da</ramdiskId>
        </item>
      </instancesSet>
    </item>
  </reservationSet>
</DescribeInstancesResponse>
""" % (aws_api,)


sample_run_instances_result = """\
<?xml version="1.0"?>
<RunInstancesResponse xmlns="http://ec2.amazonaws.com/doc/%s/">
  <reservationId>r-47a5402e</reservationId>
  <ownerId>495219933132</ownerId>
  <groupSet>
    <item>
      <groupId>default</groupId>
    </item>
  </groupSet>
  <instancesSet>
    <item>
      <instanceId>i-2ba64342</instanceId>
      <imageId>ami-60a54009</imageId>
      <instanceState>
        <code>0</code>
    <name>pending</name>
      </instanceState>
      <privateDnsName></privateDnsName>
      <dnsName></dnsName>
      <keyName>example-key-name</keyName>
       <amiLaunchIndex>0</amiLaunchIndex>
      <instanceType>m1.small</instanceType>
      <launchTime>2007-08-07T11:51:50.000Z</launchTime>
      <placement>
        <availabilityZone>us-east-1b</availabilityZone>
      </placement>
    </item>
    <item>
      <instanceId>i-2bc64242</instanceId>
      <imageId>ami-60a54009</imageId>
      <instanceState>
        <code>0</code>
    <name>pending</name>
      </instanceState>
      <privateDnsName></privateDnsName>
      <dnsName></dnsName>
      <keyName>example-key-name</keyName>
      <amiLaunchIndex>1</amiLaunchIndex>
      <instanceType>m1.small</instanceType>
      <launchTime>2007-08-07T11:51:50.000Z</launchTime>
      <placement>
        <availabilityZone>us-east-1b</availabilityZone>
      </placement>
    </item>
    <item>
      <instanceId>i-2be64332</instanceId>
      <imageId>ami-60a54009</imageId>
      <instanceState>
        <code>0</code>
    <name>pending</name>
      </instanceState>
      <privateDnsName></privateDnsName>
      <dnsName></dnsName>
      <keyName>example-key-name</keyName>
      <amiLaunchIndex>2</amiLaunchIndex>
      <instanceType>m1.small</instanceType>
      <launchTime>2007-08-07T11:51:50.000Z</launchTime>
      <placement>
        <availabilityZone>us-east-1b</availabilityZone>
      </placement>
    </item>
  </instancesSet>
</RunInstancesResponse>
""" % (aws_api,)

sample_terminate_instances_result = """\
<?xml version="1.0"?>
<TerminateInstancesResponse xmlns="http://ec2.amazonaws.com/doc/%s/">
  <instancesSet>
    <item>
      <instanceId>i-1234</instanceId>
      <shutdownState>
        <code>32</code>
        <name>shutting-down</name>
      </shutdownState>
      <previousState>
        <code>16</code>
        <name>running</name>
      </previousState>
    </item>
    <item>
      <instanceId>i-5678</instanceId>
      <shutdownState>
        <code>32</code>
        <name>shutting-down</name>
      </shutdownState>
      <previousState>
        <code>32</code>
        <name>shutting-down</name>
      </previousState>
    </item>
  </instancesSet>
</TerminateInstancesResponse>
""" % (aws_api,)


sample_describe_security_groups_result = """\
<?xml version="1.0"?>
<DescribeSecurityGroupsResponse xmlns="http://ec2.amazonaws.com/doc/%s/">
  <requestId>52b4c730-f29f-498d-94c1-91efb75994cc</requestId>
  <securityGroupInfo>
    <item>
      <ownerId>UYY3TLBUXIEON5NQVUUX6OMPWBZIQNFM</ownerId>
      <groupName>WebServers</groupName>
      <groupDescription>Web Servers</groupDescription>
      <ipPermissions>
        <item>
        <ipProtocol>tcp</ipProtocol>
      <fromPort>80</fromPort>
      <toPort>80</toPort>
      <groups/>
      <ipRanges>
        <item>
          <cidrIp>0.0.0.0/0</cidrIp>
        </item>
      </ipRanges>
        </item>
      </ipPermissions>
    </item>
  </securityGroupInfo>
</DescribeSecurityGroupsResponse>
""" % (aws_api,)


sample_describe_security_groups_multiple_result = """\
<?xml version="1.0"?>
<DescribeSecurityGroupsResponse xmlns="http://ec2.amazonaws.com/doc/%s/">
  <requestId>52b4c730-f29f-498d-94c1-91efb75994cc</requestId>
  <securityGroupInfo>
    <item>
      <ownerId>UYY3TLBUXIEON5NQVUUX6OMPWBZIQNFM</ownerId>
      <groupName>MessageServers</groupName>
      <groupDescription>Message Servers</groupDescription>
      <ipPermissions>
        <item>
        <ipProtocol>tcp</ipProtocol>
        <fromPort>80</fromPort>
        <toPort>80</toPort>
        <groups/>
        <ipRanges>
          <item>
            <cidrIp>0.0.0.0/0</cidrIp>
          </item>
        </ipRanges>
        </item>
      </ipPermissions>
    </item>
    <item>
      <ownerId>UYY3TLBUXIEON5NQVUUX6OMPWBZIQNFM</ownerId>
      <groupName>WebServers</groupName>
      <groupDescription>Web Servers</groupDescription>
      <ipPermissions>
        <item>
          <ipProtocol>tcp</ipProtocol>
          <fromPort>80</fromPort>
          <toPort>80</toPort>
          <groups/>
          <ipRanges>
            <item>
              <cidrIp>0.0.0.0/0</cidrIp>
            </item>
          </ipRanges>
        </item>
        <item>
          <ipProtocol>udp</ipProtocol>
          <fromPort>81</fromPort>
          <toPort>81</toPort>
          <groups>
            <item>
              <userId>group-user-id</userId>
              <groupName>group-name</groupName>
            </item>
          </groups>
          <ipRanges>
            <item>
              <cidrIp>0.0.0.0/16</cidrIp>
            </item>
          </ipRanges>
        </item>
      </ipPermissions>
    </item>
  </securityGroupInfo>
</DescribeSecurityGroupsResponse>
""" % (aws_api,)


sample_create_security_group = """\
<CreateSecurityGroupResponse xmlns="http://ec2.amazonaws.com/doc/%s/">
  <return>true</return>
</CreateSecurityGroupResponse>
""" % (aws_api,)


sample_duplicate_create_security_group_result = """\
<?xml version="1.0"?>
<Response>
  <Errors>
    <Error>
      <Code>InvalidGroup.Duplicate</Code>
      <Message>The security group 'group1' already exists.</Message>
    </Error>
  </Errors>
  <RequestID>89c977b5-22da-4c68-9148-9e0ebce5f68e</RequestID>
</Response>
"""

sample_invalid_create_security_group_result = """\
<?xml version="1.0"?>
<Response>
  <Errors>
    <Error>
      <Code>InvalidGroup.Reserved</Code>
      <Message>Specified group name is a reserved name.</Message>
    </Error>
  </Errors>
  <RequestID>89c977b5-22da-4c68-9148-9e0ebce5f68e</RequestID>
</Response>
"""

sample_delete_security_group = """\
<DeleteSecurityGroupResponse xmlns="http://ec2.amazonaws.com/doc/%s/">
  <return>true</return>
</DeleteSecurityGroupResponse>
""" % (aws_api,)


sample_delete_security_group_failure = """\
<?xml version="1.0"?>
<Response>
  <Errors>
    <Error>
      <Code>InvalidGroup.InUse</Code>
      <Message>Group groupID1:GroupReferredTo is used by groups: groupID2:UsingGroup</Message>
    </Error>
  </Errors>
  <RequestID>9a6df05f-9c27-47aa-81d8-6619689210cc</RequestID>
</Response>
"""


sample_authorize_security_group = """\
<AuthorizeSecurityGroupIngressResponse xmlns="http://ec2.amazonaws.com/doc/%s/">
  <return>true</return>
</AuthorizeSecurityGroupIngressResponse>
""" % (aws_api,)


sample_revoke_security_group = """\
<RevokeSecurityGroupIngressResponse xmlns="http://ec2.amazonaws.com/doc/%s/">
  <return>true</return>
</RevokeSecurityGroupIngressResponse>
""" % (aws_api,)


sample_describe_volumes_result = """\
<?xml version="1.0"?>
<DescribeVolumesResponse xmlns="http://ec2.amazonaws.com/doc/%s/">
  <volumeSet>
    <item>
      <volumeId>vol-4282672b</volumeId>
      <size>800</size>
      <status>in-use</status>
      <createTime>2008-05-07T11:51:50.000Z</createTime>
      <availabilityZone>us-east-1a</availabilityZone>
      <snapshotId>snap-12345678</snapshotId>
      <attachmentSet>
        <item>
          <volumeId>vol-4282672b</volumeId>
          <instanceId>i-6058a509</instanceId>
          <size>800</size>
          <device>/dev/sdh</device>
          <status>attached</status>
          <attachTime>2008-05-07T12:51:50.000Z</attachTime>
        </item>
      </attachmentSet>
    </item>
  </volumeSet>
</DescribeVolumesResponse>
""" % (aws_api,)


sample_describe_snapshots_result = """\
<?xml version="1.0"?>
<DescribeSnapshotsResponse xmlns="http://ec2.amazonaws.com/doc/%s/">
  <snapshotSet>
    <item>
      <snapshotId>snap-78a54011</snapshotId>
      <volumeId>vol-4d826724</volumeId>
      <status>pending</status>
      <startTime>2008-05-07T12:51:50.000Z</startTime>
      <progress>80%%</progress>
    </item>
  </snapshotSet>
</DescribeSnapshotsResponse>
""" % (aws_api,)


sample_create_volume_result = """\
<?xml version="1.0"?>
<CreateVolumeResponse xmlns="http://ec2.amazonaws.com/doc/%s/">
  <volumeId>vol-4d826724</volumeId>
  <size>800</size>
  <status>creating</status>
  <createTime>2008-05-07T11:51:50.000Z</createTime>
  <availabilityZone>us-east-1a</availabilityZone>
  <snapshotId></snapshotId>
</CreateVolumeResponse>
""" % (aws_api,)


sample_delete_volume_result = """\
<?xml version="1.0"?>
<DeleteVolumeResponse xmlns="http://ec2.amazonaws.com/doc/%s/">
  <return>true</return>
</DeleteVolumeResponse>
""" % (aws_api,)


sample_create_snapshot_result = """\
<?xml version="1.0"?>
<CreateSnapshotResponse xmlns="http://ec2.amazonaws.com/doc/%s/">
  <snapshotId>snap-78a54011</snapshotId>
  <volumeId>vol-4d826724</volumeId>
  <status>pending</status>
  <startTime>2008-05-07T12:51:50.000Z</startTime>
  <progress></progress>
</CreateSnapshotResponse>
""" % (aws_api,)


sample_delete_snapshot_result = """\
<?xml version="1.0"?>
<DeleteSnapshotResponse xmlns="http://ec2.amazonaws.com/doc/%s/">
  <return>true</return>
</DeleteSnapshotResponse>
""" % (aws_api,)


sample_attach_volume_result = """\
<?xml version="1.0"?>
<AttachVolumeResponse xmlns="http://ec2.amazonaws.com/doc/%s/">
  <volumeId>vol-4d826724</volumeId>
  <instanceId>i-6058a509</instanceId>
  <device>/dev/sdh</device>
  <status>attaching</status>
  <attachTime>2008-05-07T11:51:50.000Z</attachTime>
</AttachVolumeResponse>
""" % (aws_api,)


sample_ec2_error_message = """\
<?xml version="1.0"?>
<Response>
  <Errors>
    <Error>
      <Code>Error.Code</Code>
      <Message>Message for Error.Code</Message>
    </Error>
  </Errors>
  <RequestID>0ef9fc37-6230-4d81-b2e6-1b36277d4247</RequestID>
</Response>
"""


sample_ec2_error_messages = """\
<?xml version="1.0"?>
<Response>
  <Errors>
    <Error>
      <Code>Error.Code1</Code>
      <Message>Message for Error.Code1</Message>
    </Error>
    <Error>
      <Code>Error.Code2</Code>
      <Message>Message for Error.Code2</Message>
    </Error>
  </Errors>
  <RequestID>0ef9fc37-6230-4d81-b2e6-1b36277d4247</RequestID>
</Response>
"""


sample_single_describe_keypairs_result = """\
<?xml version="1.0"?>
<DescribeKeyPairsResponse xmlns="http://ec2.amazonaws.com/doc/%s/">
  <keySet>
    <item>
      <keyName>gsg-keypair</keyName>
      <keyFingerprint>1f:51:ae:28:bf:89:e9:d8:1f:25:5d:37:2d:7d:b8:ca:9f:f5:f1:6f</keyFingerprint>
    </item>
  </keySet>
</DescribeKeyPairsResponse>
""" % (aws_api,)


sample_multiple_describe_keypairs_result = """\
<?xml version="1.0"?>
<DescribeKeyPairsResponse xmlns="http://ec2.amazonaws.com/doc/%s/">
  <keySet>
    <item>
      <keyName>gsg-keypair-1</keyName>
      <keyFingerprint>1f:51:ae:28:bf:89:e9:d8:1f:25:5d:37:2d:7d:b8:ca:9f:f5:f1:6f</keyFingerprint>
    </item>
    <item>
      <keyName>gsg-keypair-2</keyName>
      <keyFingerprint>1f:51:ae:28:bf:89:e9:d8:1f:25:5d:37:2d:7d:b8:ca:9f:f5:f1:70</keyFingerprint>
    </item>
  </keySet>
</DescribeKeyPairsResponse>
""" % (aws_api,)


sample_create_keypair_result = """\
<?xml version="1.0"?>
<CreateKeyPairResponse xmlns="http://ec2.amazonaws.com/doc/%s/">
  <keyName>example-key-name</keyName>
  <keyFingerprint>1f:51:ae:28:bf:89:e9:d8:1f:25:5d:37:2d:7d:b8:ca:9f:f5:f1:6f</keyFingerprint>
  <keyMaterial>-----BEGIN RSA PRIVATE KEY-----
MIIEoQIBAAKCAQBuLFg5ujHrtm1jnutSuoO8Xe56LlT+HM8v/xkaa39EstM3/aFxTHgElQiJLChp
HungXQ29VTc8rc1bW0lkdi23OH5eqkMHGhvEwqa0HWASUMll4o3o/IX+0f2UcPoKCOVUR+jx71Sg
5AU52EQfanIn3ZQ8lFW7Edp5a3q4DhjGlUKToHVbicL5E+g45zfB95wIyywWZfeW/UUF3LpGZyq/
ebIUlq1qTbHkLbCC2r7RTn8vpQWp47BGVYGtGSBMpTRP5hnbzzuqj3itkiLHjU39S2sJCJ0TrJx5
i8BygR4s3mHKBj8l+ePQxG1kGbF6R4yg6sECmXn17MRQVXODNHZbAgMBAAECggEAY1tsiUsIwDl5
91CXirkYGuVfLyLflXenxfI50mDFms/mumTqloHO7tr0oriHDR5K7wMcY/YY5YkcXNo7mvUVD1pM
ZNUJs7rw9gZRTrf7LylaJ58kOcyajw8TsC4e4LPbFaHwS1d6K8rXh64o6WgW4SrsB6ICmr1kGQI7
3wcfgt5ecIu4TZf0OE9IHjn+2eRlsrjBdeORi7KiUNC/pAG23I6MdDOFEQRcCSigCj+4/mciFUSA
SWS4dMbrpb9FNSIcf9dcLxVM7/6KxgJNfZc9XWzUw77Jg8x92Zd0fVhHOux5IZC+UvSKWB4dyfcI
tE8C3p9bbU9VGyY5vLCAiIb4qQKBgQDLiO24GXrIkswF32YtBBMuVgLGCwU9h9HlO9mKAc2m8Cm1
jUE5IpzRjTedc9I2qiIMUTwtgnw42auSCzbUeYMURPtDqyQ7p6AjMujp9EPemcSVOK9vXYL0Ptco
xW9MC0dtV6iPkCN7gOqiZXPRKaFbWADp16p8UAIvS/a5XXk5jwKBgQCKkpHi2EISh1uRkhxljyWC
iDCiK6JBRsMvpLbc0v5dKwP5alo1fmdR5PJaV2qvZSj5CYNpMAy1/EDNTY5OSIJU+0KFmQbyhsbm
rdLNLDL4+TcnT7c62/aH01ohYaf/VCbRhtLlBfqGoQc7+sAc8vmKkesnF7CqCEKDyF/dhrxYdQKB
gC0iZzzNAapayz1+JcVTwwEid6j9JqNXbBc+Z2YwMi+T0Fv/P/hwkX/ypeOXnIUcw0Ih/YtGBVAC
DQbsz7LcY1HqXiHKYNWNvXgwwO+oiChjxvEkSdsTTIfnK4VSCvU9BxDbQHjdiNDJbL6oar92UN7V
rBYvChJZF7LvUH4YmVpHAoGAbZ2X7XvoeEO+uZ58/BGKOIGHByHBDiXtzMhdJr15HTYjxK7OgTZm
gK+8zp4L9IbvLGDMJO8vft32XPEWuvI8twCzFH+CsWLQADZMZKSsBasOZ/h1FwhdMgCMcY+Qlzd4
JZKjTSu3i7vhvx6RzdSedXEMNTZWN4qlIx3kR5aHcukCgYA9T+Zrvm1F0seQPbLknn7EqhXIjBaT
P8TTvW/6bdPi23ExzxZn7KOdrfclYRph1LHMpAONv/x2xALIf91UB+v5ohy1oDoasL0gij1houRe
2ERKKdwz0ZL9SWq6VTdhr/5G994CK72fy5WhyERbDjUIdHaK3M849JJuf8cSrvSb4g==
-----END RSA PRIVATE KEY-----</keyMaterial>
</CreateKeyPairResponse>
""" % (aws_api,)


sample_delete_keypair_true_result = """\
<?xml version="1.0"?>
<DeleteKeyPair xmlns="http://ec2.amazonaws.com/doc/%s/">
  <return>true</return>
</DeleteKeyPair>
""" % (aws_api,)


sample_delete_keypair_false_result = """\
<?xml version="1.0"?>
<DeleteKeyPair xmlns="http://ec2.amazonaws.com/doc/%s/">
  <return>false</return>
</DeleteKeyPair>
""" % (aws_api,)


sample_delete_keypair_no_result = """\
<?xml version="1.0"?>
<DeleteKeyPair xmlns="http://ec2.amazonaws.com/doc/%s/">
</DeleteKeyPair>
""" % (aws_api,)


sample_duplicate_keypair_result = """\
<?xml version="1.0"?>
<Response>
  <Errors>
    <Error>
      <Code>InvalidKeyPair.Duplicate</Code>
      <Message>The key pair 'key1' already exists.</Message>
    </Error>
  </Errors>
  <RequestID>89c977b5-22da-4c68-9148-9e0ebce5f68e</RequestID>
</Response>
"""


sample_allocate_address_result = """\
<?xml version="1.0"?>
<AllocateAddressResponse xmlns="http://ec2.amazonaws.com/doc/%s/">
  <publicIp>67.202.55.255</publicIp>
</AllocateAddressResponse>
""" % (aws_api,)


sample_release_address_result = """\
<?xml version="1.0"?>
<ReleaseAddressResponse xmlns="http://ec2.amazonaws.com/doc/%s/">
  <return>true</return>
</ReleaseAddressResponse>
""" % (aws_api,)


sample_associate_address_result = """\
<?xml version="1.0"?>
<AssociateAddressResponse xmlns="http://ec2.amazonaws.com/doc/%s/">
  <return>true</return>
</AssociateAddressResponse>
""" % (aws_api,)


sample_disassociate_address_result = """\
<?xml version="1.0"?>
<DisassociateAddressResponse xmlns="http://ec2.amazonaws.com/doc/%s/">
  <return>true</return>
</DisassociateAddressResponse>
""" % (aws_api,)


sample_describe_addresses_result = """\
<DescribeAddressesResponse xmlns="http://ec2.amazonaws.com/doc/%s/">
  <addressesSet>
    <item>
      <instanceId>i-28a64341</instanceId>
      <publicIp>67.202.55.255</publicIp>
    </item>
    <item>
      <publicIp>67.202.55.233</publicIp>
    </item>
  </addressesSet>
</DescribeAddressesResponse>
""" % (aws_api,)


sample_describe_availability_zones_single_result = """\
<DescribeAvailabilityZonesResponse xmlns="http://ec2.amazonaws.com/doc/%s/">
  <availabilityZoneInfo>
    <item>
      <zoneName>us-east-1a</zoneName>
      <zoneState>available</zoneState>
    </item>
  </availabilityZoneInfo>
</DescribeAvailabilityZonesResponse>
""" % (aws_api,)


sample_describe_availability_zones_multiple_results = """\
<DescribeAvailabilityZonesResponse xmlns="http://ec2.amazonaws.com/doc/%s/">
  <availabilityZoneInfo>
    <item>
      <zoneName>us-east-1a</zoneName>
      <zoneState>available</zoneState>
    </item>
    <item>
      <zoneName>us-east-1b</zoneName>
      <zoneState>available</zoneState>
    </item>
    <item>
      <zoneName>us-east-1c</zoneName>
      <zoneState>available</zoneState>
    </item>
  </availabilityZoneInfo>
</DescribeAvailabilityZonesResponse>
""" % (aws_api,)


sample_invalid_client_token_result = """\
<?xml version="1.0"?>
<Response>
  <Errors>
    <Error>
      <Code>InvalidClientTokenId</Code>
      <Message>The AWS Access Key Id you provided does not exist in our records.</Message>
    </Error>
  </Errors>
  <RequestID>47bfd77d-78d6-446d-be0d-f7621795dded</RequestID>
</Response>
"""


sample_server_internal_error_result = """\
<?xml version="1.0" encoding="UTF-8"?>
<Error>
  <Code>InternalError</Code>
  <Message>We encountered an internal error. Please try again.</Message>
  <RequestID>A2A7E5395E27DFBB</RequestID>
  <HostID>f691zulHNsUqonsZkjhILnvWwD3ZnmOM4ObM1wXTc6xuS3GzPmjArp8QC/sGsn6K</HostID>
</Error>
"""


sample_restricted_resource_result = """\
<?xml version="1.0"?>
<Response>
  <Errors>
    <Error>
      <Code>AuthFailure</Code>
      <Message>Unauthorized attempt to access restricted resource</Message>
    </Error>
  </Errors>
  <RequestID>a99e832e-e6e0-416a-9a35-81798ea521b4</RequestID>
</Response>
"""
