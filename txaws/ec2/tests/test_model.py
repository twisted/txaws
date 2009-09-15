# Copyright (C) 2009 Canonical Ltd
# Licenced under the txaws licence available at /LICENSE in the txaws source.

from txaws.ec2 import model
from txaws.testing.base import TXAWSTestCase


class SecurityGroupTestCase(TXAWSTestCase):

    def test_creation_defaults(self):
        group = model.SecurityGroup("name", "desc")
        self.assertEquals(group.name, "name")
        self.assertEquals(group.description, "desc")
        self.assertEquals(group.owner_id, "")
        self.assertEquals(group.allowed_groups, [])
        self.assertEquals(group.allowed_ips, [])

    def test_creation_all_parameters(self):
        other_groups = [
            model.SecurityGroup("other1", "another group 1"),
            model.SecurityGroup("other2", "another group 2")]
        ips = [model.IPPermission("tcp", "80", "80", "10.0.1.0/24")]
        group = model.SecurityGroup(
            "name", "desc", owner_id="me", groups=other_groups, ips=ips)
        self.assertEquals(group.name, "name")
        self.assertEquals(group.description, "desc")
        self.assertEquals(group.owner_id, "me") 
        self.assertEquals(group.allowed_groups[0].name, "other1") 
        self.assertEquals(group.allowed_groups[1].name, "other2") 
        self.assertEquals(group.allowed_ips[0].cidr_ip, "10.0.1.0/24") 
