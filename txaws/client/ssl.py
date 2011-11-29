from glob import glob
import os
import re

from OpenSSL import SSL
from OpenSSL.crypto import load_certificate, FILETYPE_PEM

from twisted.internet.ssl import CertificateOptions


__all__ = ["VerifyingContextFactory", "get_ca_certs"]


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

    def verify_callback(self, connection, x509, errno, depth, preverifyOK):
        # Only check depth == 0 on chained certificates.
        if depth == 0:
            commonName = x509.get_subject().commonName
            if commonName is None:
                return False
            # The commonName might contain a wildcard, so turn it into a
            # regex for checking.
            commonName_re = "^%s$" % commonName.replace(
                ".", "\.").replace("*", "[^.]*")
            if not re.search(commonName_re, self.host, re.I):
                return False
        return preverifyOK

    def _makeContext(self):
        context = CertificateOptions._makeContext(self)
        context.set_verify(
            SSL.VERIFY_PEER | SSL.VERIFY_FAIL_IF_NO_PEER_CERT,
            self.verify_callback)
        return context


def get_ca_certs(files="/etc/ssl/certs/*.pem"):
    """Retrieve a list of CAs pointed by C{files}."""
    certificateAuthorityMap = {}
    for certFileName in glob(files):
        # There might be some dead symlinks in there, so let's make sure it's
        # real.
        if not os.path.exists(certFileName):
            continue
        certFile = open(certFileName)
        data = certFile.read()
        certFile.close()
        x509 = load_certificate(FILETYPE_PEM, data)
        digest = x509.digest("sha1")
        # Now, de-duplicate in case the same cert has multiple names.
        certificateAuthorityMap[digest] = x509
    return certificateAuthorityMap.values()


_ca_certs = None


def get_global_ca_certs():
    """Retrieve a singleton of CA certificates."""
    global _ca_certs
    if _ca_certs is None:
        _ca_certs = get_ca_certs()
    return _ca_certs
