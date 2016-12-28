"""AWS authorization, version 4"""
import attr

import hashlib

import hmac

import urlparse
import urllib


# The following three functions are taken straight from
# http://docs.aws.amazon.com/general/latest/gr/sigv4-signed-request-examples.html
def sign(key, msg):
    return hmac.new(key, msg, hashlib.sha256).digest()


def getSignatureKey(key, dateStamp, regionName, serviceName):
    kDate = sign(('AWS4' + key), dateStamp)
    kRegion = sign(kDate, regionName)
    kService = sign(kRegion, serviceName)
    kSigning = sign(kService, 'aws4_request')
    return kSigning


def makeAMZDate(instant):
    return instant.strftime('%Y%m%dT%H%M%SZ')


def makeDateStamp(instant):
    return instant.strftime('%Y%m%d')


def _make_canonical_uri(parsed):
    """
    Return the canonical URI for a parsed URL.

    @param parsed: The parsed URL from which to extract the canonical
        URI
    @type parsed: L{urlparse.ParseResult}

    @return: The canonical URI.
    @rtype: L{str}
    """
    canonical_parsed = parsed._replace(params='', query='', fragment='')
    return urlparse.urlunparse(canonical_parsed)


def _make_canonical_query_string(parsed):
    """
    Return the canonical query string for a parsed URL.

    @param parsed: The parsed URL from which to extract the canonical
        query string.
    @type parsed: L{urlparse.ParseResult}

    @return: The canonical query string.
    @rtype: L{str}
    """
    query_params = urlparse.parse_qs(parsed.query, keep_blank_values=True)
    sorted_query_params = sorted((k, v)
                                 for k, vs in query_params.items()
                                 for v in vs)
    return urllib.urlencode(sorted_query_params)


def _make_canonical_headers(headers, headers_to_sign):
    """
    Return canonicalized headers.

    @param headers: The request headers.
    @type headers: L{dict}

    @param headers_to_sign: A sequence of header names that should be
        signed.
    @type headers_to_sign: L{str}

    @return: The canonicalized headers.
    @rtype: L{str}
    """
    pairs = [(name.lower(), str(headers[name]).strip())
             for name in headers_to_sign
             if name in headers]
    sorted_pairs = sorted('{}:{}'.format(name, value)
                          for name, value in sorted(pairs))
    return '\n'.join(sorted_pairs) + '\n'


def _make_signed_headers(headers, headers_to_sign):
    """
    Return a semicolon-delimited list of headers to sign.

    @param headers: The request headers.
    @type headers: L{dict}

    @param headers_to_sign: A sequence of header names that should be
        signed.
    @type headers_to_sign: L{str}

    @return: The semicolon-delimited list of headers.
    @rtype: L{str}
    """
    return ";".join(header.lower() for header in sorted(headers_to_sign)
                    if header in headers)


@attr.s
class _CanonicalRequest(object):
    """
    A canonicalized request.
    """
    method = attr.ib()
    canonical_uri = attr.ib()
    canonical_query_string = attr.ib()
    canonical_headers = attr.ib()
    signed_headers = attr.ib()
    payload_hash = attr.ib()

    @classmethod
    def from_payload_and_headers(cls,
                                 method,
                                 url,
                                 headers,
                                 headers_to_sign,
                                 payload):
        """
        Construct a L{_CanonicalRequest} from the provided headers and
        payload.

        @param method: The HTTP method.
        @type method: L{str}

        @param url: The request's URL
        @type url: L{str}

        @param headers: The request's headers.
        @type headers: L{dict}

        @param headers_to_sign: A sequence of header names that should
            be signed.
        @type headers_to_sign: L{str}

        @param payload: The request's payload.
        @type payload: L{str}

        @return: A canonical request
        @rtype: L{_CanonicalRequest}
        """
        parsed = urlparse.urlparse(url)
        return cls(
            method=method,
            canonical_uri=_make_canonical_uri(parsed),
            canonical_query_string=_make_canonical_query_string(parsed),
            canonical_headers=_make_canonical_headers(headers,
                                                      headers_to_sign),
            signed_headers=_make_signed_headers(headers, headers_to_sign),
            payload_hash=hashlib.sha256(payload).hexdigest(),
        )

    def serialize(self):
        """
        Serialize this canonical request to a string.
        """
        return '\n'.join(attr.astuple(self))

    def hash(self):
        return hashlib.sha256(self.serialize()).hexdigest()


@attr.s
class _CredentialScope(object):
    """
    The scope of the AWS credentials.
    """

    date_stamp = attr.ib()
    region = attr.ib()
    service = attr.ib()

    def serialize(self):
        """
        Serialize this credential scope to a string.
        """
        return "/".join(attr.astuple(self) + ('aws4_request',))


@attr.s
class _Credential(object):
    """
    An AWS credential.
    """
    access_key = attr.ib()
    credential_scope = attr.ib()

    def serialize(self):
        """
        Serialize this credential bundle to a string.
        """
        return "/".join([self.access_key, self.credential_scope.serialize()])


@attr.s
class _SignableAWS4HMAC256Token(object):
    ALGORITHM = "AWS4-HMAC-SHA256"

    amz_date = attr.ib()
    credential_scope = attr.ib()
    canonical_request = attr.ib()

    def serialize(self):
        """
        Serialize this token to a string.
        """
        return "\n".join([
            self.ALGORITHM,
            self.amz_date,
            self.credential_scope.serialize(),
            self.canonical_request.hash(),
        ])

    def signature(self, signing_key):
        """
        Return the signature of this token.
        """
        return hmac.new(
            signing_key,
            self.serialize(),
            hashlib.sha256,
        ).hexdigest()


def _make_authorization_header(region,
                               service,
                               canonical_request,
                               credentials,
                               instant):
    """
    Construct an AWS version 4 authorization value for use in an
    C{Authorization} header.

    @param region: The AWS region name (e.g., C{us-east-1}).
    @type region: L{str}

    @param service: The AWS service's name (e.g., C{s3}).
    @type service: L{str}

    @param canonical_request: The canonical form of the request.
    @type canonical_request: L{_CanonicalRequest} (use
        L{_CanonicalRequest.from_payload_and_headers})

    @param credentials: The AWS credentials.
    @type credentials: L{txaws.credentials.AWSCredentials}

    @param instant: The current UTC date and time
    @type instant: A naive local L{datetime.datetime} (as returned by
        L{datetime.datetime.utcnow})

    @return: A value suitable for use in an C{Authorization} header
    @rtype: L{str}
    """
    date_stamp = makeDateStamp(instant)
    amz_date = makeAMZDate(instant)

    scope = _CredentialScope(
        date_stamp=date_stamp,
        region=region,
        service=service
    )

    signable = _SignableAWS4HMAC256Token(
        amz_date,
        scope,
        canonical_request,
    )

    signature = signable.signature(
        getSignatureKey(credentials.secret_key,
                        date_stamp,
                        region,
                        service)
    )

    v4credential = _Credential(
        access_key=credentials.access_key,
        credential_scope=scope,
    )

    return (
        "{} ".format(_SignableAWS4HMAC256Token.ALGORITHM) +
        ", ".join([
            "Credential={}".format(v4credential.serialize()),
            "SignedHeaders={}".format(canonical_request.signed_headers),
            "Signature={}".format(signature),
        ]))
