from txaws import version


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
""" % (version.ec2_api,)


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
""" % (version.ec2_api,)


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
""" % (version.ec2_api,)

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
""" % (version.ec2_api,)


sample_describe_security_groups_with_openstack = """\
<?xml version="1.0"?>
<DescribeSecurityGroupsResponse xmlns="http://ec2.amazonaws.com/doc/%s/">
  <requestId>7d4e4dbd-0a33-4d3a-864a-b5ce0f1c9cbf</requestId>
  <securityGroupInfo>
    <item>
      <ipPermissions>
        <item>
          <toPort>22</toPort>
          <ipProtocol>tcp</ipProtocol>
          <ipRanges>
             <item><cidrIp>0.0.0.0/0</cidrIp></item>
          </ipRanges>
          <groups/>
          <fromPort>22</fromPort>
        </item>
        <item>
         <toPort/>
         <ipProtocol/>
         <ipRanges/>
         <groups>
            <item>
              <groupName>WebServers</groupName>
              <userId>UYY3TLBUXIEON5NQVUUX6OMPWBZIQNFM</userId>
            </item>
         </groups>
         <fromPort/>
        </item>
      </ipPermissions>
      <groupName>WebServers</groupName>
      <groupDescription>Web servers</groupDescription>
      <ownerId>UYY3TLBUXIEON5NQVUUX6OMPWBZIQNFM</ownerId>
    </item>
  </securityGroupInfo>
</DescribeSecurityGroupsResponse>
""" % (version.ec2_api,)

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
""" % (version.ec2_api,)


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
          <ipProtocol>tcp</ipProtocol>
          <fromPort>0</fromPort>
          <toPort>65535</toPort>
          <groups>
            <item>
              <userId>group-user-id</userId>
              <groupName>group-name1</groupName>
            </item>
          </groups>
          <ipRanges />
        </item>
        <item>
          <ipProtocol>udp</ipProtocol>
          <fromPort>0</fromPort>
          <toPort>65535</toPort>
          <groups>
            <item>
              <userId>group-user-id</userId>
              <groupName>group-name1</groupName>
            </item>
          </groups>
          <ipRanges />
        </item>
        <item>
          <ipProtocol>icmp</ipProtocol>
          <fromPort>-1</fromPort>
          <toPort>-1</toPort>
          <groups>
            <item>
              <userId>group-user-id</userId>
              <groupName>group-name1</groupName>
            </item>
          </groups>
          <ipRanges />
        </item>
        <item>
          <ipProtocol>tcp</ipProtocol>
          <fromPort>0</fromPort>
          <toPort>65535</toPort>
          <groups>
            <item>
              <userId>group-user-id</userId>
              <groupName>group-name2</groupName>
            </item>
          </groups>
          <ipRanges />
        </item>
        <item>
          <ipProtocol>udp</ipProtocol>
          <fromPort>0</fromPort>
          <toPort>65535</toPort>
          <groups>
            <item>
              <userId>group-user-id</userId>
              <groupName>group-name2</groupName>
            </item>
          </groups>
          <ipRanges />
        </item>
        <item>
          <ipProtocol>icmp</ipProtocol>
          <fromPort>-1</fromPort>
          <toPort>-1</toPort>
          <groups>
            <item>
              <userId>group-user-id</userId>
              <groupName>group-name2</groupName>
            </item>
          </groups>
          <ipRanges />
        </item>
      </ipPermissions>
    </item>
  </securityGroupInfo>
</DescribeSecurityGroupsResponse>
""" % (version.ec2_api,)


sample_describe_security_groups_multiple_groups = """\
<?xml version="1.0"?>
<DescribeSecurityGroupsResponse xmlns="http://ec2.amazonaws.com/doc/%s/">
<requestId>481987ac-07e2-4f34-99b9-38bcce029ce9</requestId>
<securityGroupInfo>
  <item>
    <ownerId>170743011661</ownerId>
    <groupName>web/ssh</groupName>
    <groupDescription>Web and SSH access</groupDescription>
    <ipPermissions>
      <item>
        <ipProtocol>icmp</ipProtocol>
        <fromPort>-1</fromPort>
        <toPort>-1</toPort>
        <groups>
          <item>
            <userId>170723411662</userId>
            <groupName>default</groupName>
          </item>
          <item>
            <userId>175723011368</userId>
            <groupName>test1</groupName>
          </item>
        </groups>
        <ipRanges/>
      </item>
      <item>
        <ipProtocol>tcp</ipProtocol>
        <fromPort>1</fromPort>
        <toPort>65535</toPort>
        <groups>
          <item>
            <userId>170723411662</userId>
            <groupName>default</groupName>
          </item>
          <item>
            <userId>175723011368</userId>
            <groupName>test1</groupName>
          </item>
        </groups>
        <ipRanges/>
      </item>
      <item>
        <ipProtocol>udp</ipProtocol>
        <fromPort>1</fromPort>
        <toPort>65535</toPort>
        <groups>
          <item>
            <userId>170723411662</userId>
            <groupName>default</groupName>
          </item>
          <item>
            <userId>175723011368</userId>
            <groupName>test1</groupName>
          </item>
        </groups>
        <ipRanges/>
      </item>
      <item>
        <ipProtocol>tcp</ipProtocol>
        <fromPort>22</fromPort>
        <toPort>22</toPort>
        <groups/>
        <ipRanges>
          <item>
            <cidrIp>0.0.0.0/0</cidrIp>
          </item>
        </ipRanges>
      </item>
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
""" % (version.ec2_api,)


sample_create_security_group = """\
<CreateSecurityGroupResponse xmlns="http://ec2.amazonaws.com/doc/%s/">
  <return>true</return>
</CreateSecurityGroupResponse>
""" % (version.ec2_api,)


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
""" % (version.ec2_api,)


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
""" % (version.ec2_api,)


sample_revoke_security_group = """\
<RevokeSecurityGroupIngressResponse xmlns="http://ec2.amazonaws.com/doc/%s/">
  <return>true</return>
</RevokeSecurityGroupIngressResponse>
""" % (version.ec2_api,)


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
""" % (version.ec2_api,)


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
""" % (version.ec2_api,)


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
""" % (version.ec2_api,)


sample_delete_volume_result = """\
<?xml version="1.0"?>
<DeleteVolumeResponse xmlns="http://ec2.amazonaws.com/doc/%s/">
  <return>true</return>
</DeleteVolumeResponse>
""" % (version.ec2_api,)


sample_create_snapshot_result = """\
<?xml version="1.0"?>
<CreateSnapshotResponse xmlns="http://ec2.amazonaws.com/doc/%s/">
  <snapshotId>snap-78a54011</snapshotId>
  <volumeId>vol-4d826724</volumeId>
  <status>pending</status>
  <startTime>2008-05-07T12:51:50.000Z</startTime>
  <progress></progress>
</CreateSnapshotResponse>
""" % (version.ec2_api,)


sample_delete_snapshot_result = """\
<?xml version="1.0"?>
<DeleteSnapshotResponse xmlns="http://ec2.amazonaws.com/doc/%s/">
  <return>true</return>
</DeleteSnapshotResponse>
""" % (version.ec2_api,)


sample_attach_volume_result = """\
<?xml version="1.0"?>
<AttachVolumeResponse xmlns="http://ec2.amazonaws.com/doc/%s/">
  <volumeId>vol-4d826724</volumeId>
  <instanceId>i-6058a509</instanceId>
  <device>/dev/sdh</device>
  <status>attaching</status>
  <attachTime>2008-05-07T11:51:50.000Z</attachTime>
</AttachVolumeResponse>
""" % (version.ec2_api,)


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
""" % (version.ec2_api,)


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
""" % (version.ec2_api,)


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
""" % (version.ec2_api,)


sample_delete_keypair_true_result = """\
<?xml version="1.0"?>
<DeleteKeyPair xmlns="http://ec2.amazonaws.com/doc/%s/">
  <return>true</return>
</DeleteKeyPair>
""" % (version.ec2_api,)


sample_delete_keypair_false_result = """\
<?xml version="1.0"?>
<DeleteKeyPair xmlns="http://ec2.amazonaws.com/doc/%s/">
  <return>false</return>
</DeleteKeyPair>
""" % (version.ec2_api,)


sample_delete_keypair_no_result = """\
<?xml version="1.0"?>
<DeleteKeyPair xmlns="http://ec2.amazonaws.com/doc/%s/">
</DeleteKeyPair>
""" % (version.ec2_api,)


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


sample_import_keypair_result = """\
<?xml version="1.0"?>
<ImportKeyPairResponse xmlns="http://ec2.amazonaws.com/doc/%s/">
  <keyName>example-key-name</keyName>
  <keyFingerprint>1f:51:ae:28:bf:89:e9:d8:1f:25:5d:37:2d:7d:b8:ca:9f:f5:f1:6f</keyFingerprint>
</ImportKeyPairResponse>
""" % (version.ec2_api,)


sample_allocate_address_result = """\
<?xml version="1.0"?>
<AllocateAddressResponse xmlns="http://ec2.amazonaws.com/doc/%s/">
  <publicIp>67.202.55.255</publicIp>
</AllocateAddressResponse>
""" % (version.ec2_api,)


sample_release_address_result = """\
<?xml version="1.0"?>
<ReleaseAddressResponse xmlns="http://ec2.amazonaws.com/doc/%s/">
  <return>true</return>
</ReleaseAddressResponse>
""" % (version.ec2_api,)


sample_associate_address_result = """\
<?xml version="1.0"?>
<AssociateAddressResponse xmlns="http://ec2.amazonaws.com/doc/%s/">
  <return>true</return>
</AssociateAddressResponse>
""" % (version.ec2_api,)


sample_disassociate_address_result = """\
<?xml version="1.0"?>
<DisassociateAddressResponse xmlns="http://ec2.amazonaws.com/doc/%s/">
  <return>true</return>
</DisassociateAddressResponse>
""" % (version.ec2_api,)


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
""" % (version.ec2_api,)


sample_describe_availability_zones_single_result = """\
<DescribeAvailabilityZonesResponse xmlns="http://ec2.amazonaws.com/doc/%s/">
  <availabilityZoneInfo>
    <item>
      <zoneName>us-east-1a</zoneName>
      <zoneState>available</zoneState>
    </item>
  </availabilityZoneInfo>
</DescribeAvailabilityZonesResponse>
""" % (version.ec2_api,)


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
""" % (version.ec2_api,)


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


sample_server_internal_error_result = """\
<?xml version="1.0" encoding="UTF-8"?>
<Error>
  <Code>InternalError</Code>
  <Message>We encountered an internal error. Please try again.</Message>
  <RequestID>A2A7E5395E27DFBB</RequestID>
  <HostID>f691zulHNsUqonsZkjhILnvWwD3ZnmOM4ObM1wXTc6xuS3GzPmjArp8QC/sGsn6K</HostID>
</Error>
"""


sample_list_buckets_result = """\
<?xml version="1.0" encoding="UTF-8"?>
<ListAllMyBucketsResult xmlns="http://s3.amazonaws.com/doc/%s/">
  <Owner>
    <ID>bcaf1ffd86f41caff1a493dc2ad8c2c281e37522a640e161ca5fb16fd081034f</ID>
    <DisplayName>webfile</DisplayName>
  </Owner>
  <Buckets>
    <Bucket>
      <Name>quotes</Name>
      <CreationDate>2006-02-03T16:45:09.000Z</CreationDate>
    </Bucket>
    <Bucket>
      <Name>samples</Name>
      <CreationDate>2006-02-03T16:41:58.000Z</CreationDate>
    </Bucket>
  </Buckets>
</ListAllMyBucketsResult>
""" % (version.s3_api,)


sample_get_bucket_result = """\
<?xml version="1.0" encoding="UTF-8"?>
<ListBucketResult xmlns="http://s3.amazonaws.com/doc/%s/">
  <Name>mybucket</Name>
  <Prefix>N</Prefix>
  <Marker>Ned</Marker>
  <MaxKeys>40</MaxKeys>
  <IsTruncated>false</IsTruncated>
  <Contents>
    <Key>Nelson</Key>
    <LastModified>2006-01-01T12:00:00.000Z</LastModified>
    <ETag>&quot;828ef3fdfa96f00ad9f27c383fc9ac7f&quot;</ETag>
    <Size>5</Size>
    <StorageClass>STANDARD</StorageClass>
    <Owner>
      <ID>bcaf1ffd86f41caff1a493dc2ad8c2c281e37522a640e161ca5fb16fd081034f</ID>
      <DisplayName>webfile</DisplayName>
     </Owner>
  </Contents>
  <Contents>
    <Key>Neo</Key>
    <LastModified>2006-01-01T12:00:00.000Z</LastModified>
    <ETag>&quot;828ef3fdfa96f00ad9f27c383fc9ac7f&quot;</ETag>
    <Size>4</Size>
    <StorageClass>STANDARD</StorageClass>
     <Owner>
      <ID>bcaf1ffd86f41caff1a493dc2ad8c2c281e37522a640e161ca5fb16fd081034f</ID>
      <DisplayName>webfile</DisplayName>
    </Owner>
 </Contents>
</ListBucketResult>
""" % (version.s3_api,)


sample_get_bucket_location_result = """\
<LocationConstraint xmlns="http://s3.amazonaws.com/doc/2006-03-01/">EU</LocationConstraint>

"""
sample_request_payment = """\
<?xml version="1.0" encoding="UTF-8"?>
<RequestPaymentConfiguration xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
  <Payer>Requester</Payer>
</RequestPaymentConfiguration>
"""

sample_s3_signature_mismatch = """\
<?xml version="1.0" encoding="UTF-8"?>
<Error>
  <Code>SignatureDoesNotMatch</Code>
  <Message>The request signature we calculated does not match the signature you provided. Check your key and signing method.</Message>
  <StringToSignBytes>47 45 54 0a 31 42 32 4d 32 59 38 41 73 67 54 70 67 41 6d 59 37 50 68 43 66 67 3d 3d 0a 0a 54 68 75 2c 20 30 35 20 4e 6f 76 20 32 30 30 39 20 32 31 3a 33 33 3a 32 39 20 47 4d 54 0a 2f</StringToSignBytes>
  <RequestId>AB9216C8640751B2</RequestId>
  <HostId>sAPBpmFdsOsgUUwtSLsiT6KIwP1mPbmrYY0xUoahzJE263qmABkTaqzGhHddgOq5</HostId>
  <SignatureProvided>ltowhdrbjaQ8dQc9VS5MxzJfsPJZi0BZHEzJC3r9pzU=</SignatureProvided>
  <StringToSign>GET\n1B2M2Y8AsgTpgAmY7PhCfg==\n\nThu, 05 Nov 2009 21:33:29 GMT\n/</StringToSign>
  <AWSAccessKeyId>SOMEKEYID</AWSAccessKeyId>
</Error>
"""


sample_s3_invalid_access_key_result = """\
<?xml version="1.0" encoding="UTF-8"?>
<Error>
  <Code>InvalidAccessKeyId</Code>
  <Message>The AWS Access Key Id you provided does not exist in our records.</Message>
  <RequestId>0223AD81A94821CE</RequestId>
  <HostId>HAw5g9P1VkN8ztgLKFTK20CY5LmCfTwXcSths1O7UQV6NuJx2P4tmFnpuOsziwOE</HostId>
  <AWSAccessKeyId>SOMEKEYID</AWSAccessKeyId>
</Error>
"""

sample_access_control_policy_result = """\
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
</AccessControlPolicy>"""

