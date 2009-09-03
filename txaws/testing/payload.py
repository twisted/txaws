from txaws.version import aws_api


sample_required_describe_instances_result = """<?xml version="1.0"?>
<DescribeInstancesResponse xmlns="http://ec2.amazonaws.com/doc/""" + aws_api + """/">
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
"""


sample_describe_instances_result = """<?xml version="1.0"?>
<DescribeInstancesResponse xmlns="http://ec2.amazonaws.com/doc/""" + aws_api + """/">
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
"""


sample_terminate_instances_result = """<?xml version="1.0"?>
<TerminateInstancesResponse xmlns="http://ec2.amazonaws.com/doc/""" + aws_api + """/">
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
"""


sample_describe_volumes_result = """<?xml version="1.0"?>
<DescribeVolumesResponse xmlns="http://ec2.amazonaws.com/doc/""" + aws_api + """/">
  <volumeSet>
    <item>
      <volumeId>vol-4282672b</volumeId>
      <size>800</size>
      <status>in-use</status>
      <createTime>2008-05-07T11:51:50.000Z</createTime>
      <attachmentSet>
        <item>
          <volumeId>vol-4282672b</volumeId>
          <instanceId>i-6058a509</instanceId>
          <size>800</size>
          <snapshotId>snap-12345678</snapshotId>
          <availabilityZone>us-east-1a</availabilityZone>
          <status>attached</status>
          <attachTime>2008-05-07T12:51:50.000Z</attachTime>
        </item>
      </attachmentSet>
    </item>
  </volumeSet>
</DescribeVolumesResponse>
"""


sample_describe_snapshots_result = """<?xml version="1.0"?>
<DescribeSnapshotsResponse xmlns="http://ec2.amazonaws.com/doc/""" + aws_api + """/">
  <snapshotSet>
    <item>
      <snapshotId>snap-78a54011</snapshotId>
      <volumeId>vol-4d826724</volumeId>
      <status>pending</status>
      <startTime>2008-05-07T12:51:50.000Z</startTime>
      <progress>80%</progress>
    </item>
  </snapshotSet>
</DescribeSnapshotsResponse>
"""


sample_create_volume_result = """<?xml version="1.0"?>
<CreateVolumeResponse xmlns="http://ec2.amazonaws.com/doc/""" + aws_api + """/">
  <volumeId>vol-4d826724</volumeId>
  <size>800</size>
  <status>creating</status>
  <createTime>2008-05-07T11:51:50.000Z</createTime>
  <availabilityZone>us-east-1a</availabilityZone>
  <snapshotId></snapshotId>
</CreateVolumeResponse>
"""


sample_delete_volume_result = """<?xml version="1.0"?>
<DeleteVolumeResponse xmlns="http://ec2.amazonaws.com/doc/""" + aws_api + """/">
  <return>true</return>
</DeleteVolumeResponse>
"""


sample_create_snapshot_result = """<?xml version="1.0"?>
<CreateSnapshotResponse xmlns="http://ec2.amazonaws.com/doc/""" + aws_api + """/">
  <snapshotId>snap-78a54011</snapshotId>
  <volumeId>vol-4d826724</volumeId>
  <status>pending</status>
  <startTime>2008-05-07T12:51:50.000Z</startTime>
  <progress></progress>
</CreateSnapshotResponse>
"""


sample_delete_snapshot_result = """<?xml version="1.0"?>
<DeleteSnapshotResponse xmlns="http://ec2.amazonaws.com/doc/""" + aws_api + """/">
  <return>true</return>
</DeleteSnapshotResponse>
"""


sample_attach_volume_result = """<?xml version="1.0"?>
<AttachVolumeResponse xmlns="http://ec2.amazonaws.com/doc/""" + aws_api + """/">
  <volumeId>vol-4d826724</volumeId>
  <instanceId>i-6058a509</instanceId>
  <device>/dev/sdh</device>
  <status>attaching</status>
  <attachTime>2008-05-07T11:51:50.000Z</attachTime>
</AttachVolumeResponse>
"""


sample_single_describe_keypairs_result = """<?xml version="1.0"?>
<DescribeKeyPairsResponse xmlns="http://ec2.amazonaws.com/doc/""" + aws_api + """/">
  <keySet>
    <item>
      <keyName>gsg-keypair</keyName>
      <keyFingerprint>1f:51:ae:28:bf:89:e9:d8:1f:25:5d:37:2d:7d:b8:ca:9f:f5:f1:6f</keyFingerprint>
    </item>
  </keySet>
</DescribeKeyPairsResponse>
"""


sample_multiple_describe_keypairs_result = """<?xml version="1.0"?>
<DescribeKeyPairsResponse xmlns="http://ec2.amazonaws.com/doc/""" + aws_api + """/">
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
"""


sample_create_keypair_result = """<?xml version="1.0"?>
<CreateKeyPairResponse xmlns="http://ec2.amazonaws.com/doc/""" + aws_api + """/">
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
"""


sample_delete_keypair_true_result = """<?xml version="1.0"?>
<DeleteKeyPair xmlns="http://ec2.amazonaws.com/doc/""" + aws_api + """/">
  <return>true</return>
</DeleteKeyPair>
"""


sample_delete_keypair_false_result = """<?xml version="1.0"?>
<DeleteKeyPair xmlns="http://ec2.amazonaws.com/doc/""" + aws_api + """/">
  <return>false</return>
</DeleteKeyPair>
"""


sample_delete_keypair_no_result = """<?xml version="1.0"?>
<DeleteKeyPair xmlns="http://ec2.amazonaws.com/doc/""" + aws_api + """/">
</DeleteKeyPair>
"""
