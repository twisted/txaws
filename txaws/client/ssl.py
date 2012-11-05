from glob import glob
import os
import re
import sys

from OpenSSL import SSL
from OpenSSL.crypto import load_certificate, FILETYPE_PEM

from twisted.internet.ssl import CertificateOptions

from txaws import exception


__all__ = ["VerifyingContextFactory", "get_ca_certs"]


# Multiple defaults are supported; just add more paths, separated by colons.
if sys.platform == "darwin":
    DEFAULT_CERTS_PATH = "/System/Library/OpenSSL/certs/"
# XXX Windows users can file a bug to add theirs, since we don't know what
# the right path is
else:
    DEFAULT_CERTS_PATH = "/etc/ssl/certs/"


class VerifyingContextFactory(CertificateOptions):
    """
    A SSL context factory to pass to C{connectSSL} to check for hostname
    validity.
    """

    def __init__(self, host, caCerts=None):
        if caCerts is None:
            caCerts = get_global_ca_certs()
        CertificateOptions.__init__(self, verify=True, caCerts=caCerts)
        self.host = host

    def _dnsname_match(self, dn, host):
        pats = []
        for frag in dn.split(r"."):
            if frag == "*":
                pats.append("[^.]+")
            else:
                frag = re.escape(frag)
                pats.append(frag.replace(r"\*", "[^.]*"))

        rx = re.compile(r"\A" + r"\.".join(pats) + r"\Z", re.IGNORECASE)
        return bool(rx.match(host))

    def verify_callback(self, connection, x509, errno, depth, preverifyOK):
        # Only check depth == 0 on chained certificates.
        if depth == 0:
            dns_found = False
            if getattr(x509, "get_extension", None) is not None:
                for index in range(x509.get_extension_count()):
                    extension = x509.get_extension(index)
                    if extension.get_short_name() != "subjectAltName":
                        continue
                    data = str(extension)
                    for element in data.split(", "):
                        key, value = element.split(":")
                        if key != "DNS":
                            continue
                        if self._dnsname_match(value, self.host):
                            return preverifyOK
                        dns_found = True
                    break
            if not dns_found:
                commonName = x509.get_subject().commonName
                if commonName is None:
                    return False
                if not self._dnsname_match(commonName, self.host):
                    return False
            else:
                return False
        return preverifyOK

    def _makeContext(self):
        context = CertificateOptions._makeContext(self)
        context.set_verify(
            SSL.VERIFY_PEER | SSL.VERIFY_FAIL_IF_NO_PEER_CERT,
            self.verify_callback)
        return context


def get_ca_certs():
    """
    Retrieve a list of CAs at either the DEFAULT_CERTS_PATH or the env
    override, TXAWS_CERTS_PATH.

    In order to find .pem files, this function checks first for presence of the
    TXAWS_CERTS_PATH environment variable that should point to a directory
    containing cert files. In the absense of this variable, the module-level
    DEFAULT_CERTS_PATH will be used instead.

    Note that both of these variables have have multiple paths in them, just
    like the familiar PATH environment variable (separated by colons).
    """
    cert_paths = os.getenv("TXAWS_CERTS_PATH", DEFAULT_CERTS_PATH).split(":")
    certificate_authority_map = {}
    for path in cert_paths:
        if not path:
            continue
        for cert_file_name in glob(os.path.join(path, "*.pem")):
            # There might be some dead symlinks in there, so let's make sure
            # it's real.
            if not os.path.exists(cert_file_name):
                continue
            cert_file = open(cert_file_name)
            data = cert_file.read()
            cert_file.close()
            x509 = load_certificate(FILETYPE_PEM, data)
            digest = x509.digest("sha1")
            # Now, de-duplicate in case the same cert has multiple names.
            certificate_authority_map[digest] = x509
    values = certificate_authority_map.values()
    if len(values) == 0:
        raise exception.CertsNotFoundError("Could not find any .pem files.")
    return values


_ca_certs = None


def get_global_ca_certs():
    """Retrieve a singleton of CA certificates."""
    global _ca_certs
    if _ca_certs is None:
        _ca_certs = get_ca_certs()
    return _ca_certs
