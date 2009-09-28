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
        user = "somegal24"
        other_groups = [
            model.SecurityGroup("other1", "another group 1"),
            model.SecurityGroup("other2", "another group 2")]
        user_group_pairs = [
            model.UserIDGroupPair(user, other_groups[0].name),
            model.UserIDGroupPair(user, other_groups[1].name)]
        ips = [model.IPPermission("tcp", "80", "80", "10.0.1.0/24")]
        group = model.SecurityGroup(
            "name", "desc", owner_id="me", groups=user_group_pairs, ips=ips)
        self.assertEquals(group.name, "name")
        self.assertEquals(group.description, "desc")
        self.assertEquals(group.owner_id, "me") 
        self.assertEquals(group.allowed_groups[0].user_id, "somegal24") 
        self.assertEquals(group.allowed_groups[0].group_name, "other1") 
        self.assertEquals(group.allowed_groups[1].user_id, "somegal24") 
        self.assertEquals(group.allowed_groups[1].group_name, "other2") 
        self.assertEquals(group.allowed_ips[0].cidr_ip, "10.0.1.0/24") 


class UserIDGroupPairTestCase(TXAWSTestCase):

    def test_creation(self):
        user_id = "cowboy22"
        group_name = "Rough Riders"
        user_group_pair = model.UserIDGroupPair(user_id, group_name)
        self.assertEquals(user_group_pair.user_id, "cowboy22")
        self.assertEquals(user_group_pair.group_name, "Rough Riders")
