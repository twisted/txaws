from txaws.util import XML


PERMISSIONS = ("FULL_CONTROL",
               "WRITE",
               "WRITE_ACP",
               "READ",
               "READ_ACP")


class XMLMixin(object):

    def to_xml(self):
        return "".join(self._to_xml())


class AccessControlPolicy(XMLMixin):

    def __init__(self, owner=None, access_control_list=()):
        self.owner = owner
        self.access_control_list = access_control_list

    def _to_xml(self, buffer=None):
        if buffer is None:
            buffer = []
        buffer.append("<AccessControlPolicy>\n")
        if self.owner:
            self.owner._to_xml(buffer=buffer, indent=1)
        buffer.append("  <AccessControlList>\n")
        for grant in self.access_control_list:
            grant._to_xml(buffer=buffer, indent=2)
        buffer.append("  </AccessControlList>\n"
                   "</AccessControlPolicy>")
        return buffer

    @classmethod
    def from_xml(cls, xml_bytes):
        root = XML(xml_bytes)
        owner_node = root.find("Owner")
        owner = Owner(owner_node.findtext("ID"),
                      owner_node.findtext("DisplayName"))
        acl_node = root.find("AccessControlList")
        acl = []
        for grant_node in acl_node.findall("Grant"):
            grantee_node = grant_node.find("Grantee")
            grantee = Grantee(grantee_node.findtext("ID"),
                              grantee_node.findtext("DisplayName"))
            permission = grant_node.findtext("Permission")
            acl.append(Grant(grantee, permission))
        return cls(owner, acl)


class Grant(XMLMixin):

    def __init__(self, grantee, permission=None):
        self.grantee = grantee
        self.permission = permission

    def _set_permission(self, perm):
        if perm not in PERMISSIONS:
            raise ValueError("Invalid permission '%s'. Must be one of %s" %
                             (perm, ",".join(PERMISSIONS)))
        self._permission = perm

    def _get_permission(self):
        return self._permission

    permission = property(_get_permission, _set_permission)

    def _to_xml(self, buffer=None, indent=0):
        if buffer is None:
            buffer = []
        ws = " " * (indent * 2)
        buffer.append(ws + "<Grant>\n")
        if self.grantee:
            self.grantee._to_xml(buffer, indent + 1)
        if self.permission:
            buffer.append("%s  <Permission>%s</Permission>\n" % (
                          ws, self.permission))
        buffer.append(ws + "</Grant>\n")
        return buffer


class Owner(XMLMixin):

    def __init__(self, id, display_name):
        self.id = id
        self.display_name = display_name

    def _to_xml(self, buffer=None, indent=0):
        if buffer is None:
            buffer = []
        ws = " " * (indent * 2)
        buffer.append("%s<Owner>\n"
                      "%s  <ID>%s</ID>\n"
                      "%s  <DisplayName>%s</DisplayName>\n"
                      "%s</Owner>\n" % (ws, ws, self.id, ws, self.display_name,
                                        ws))
        return buffer


class Grantee(Owner):

    def _to_xml(self, buffer=None, indent=0):
        if buffer is None:
            buffer = []
        ws = " " * (indent * 2)
        buffer.append("%s<Grantee "
                      'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
                      ' xsi:type="CanonicalUser">\n'
                      "%s  <ID>%s</ID>\n"
                      "%s  <DisplayName>%s</DisplayName>\n"
                      "%s</Grantee>\n" % (ws, ws, self.id, ws,
                                          self.display_name, ws))
        return buffer
