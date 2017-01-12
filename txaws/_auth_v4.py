# Licenced under the txaws licence available at /LICENSE in the txaws source.
"""
AWS authorization, version 4.
"""
import hashlib
import hmac
import urllib
import urlparse

import attr

# The following four functions are taken straight from
# http://docs.aws.amazon.com/general/latest/gr/sigv4-signed-request-examples.html
def sign(key, msg):
    """
    Produce a SHA-256 HMAC for a message.

    @param key: The secret key to use.
    @type key: L{bytes}

    @param msg: The message to sign.
    @type msg: L{bytes}

    @return: The binary (B{not} the hex) digest of the HMAC signature.
    """
    return hmac.new(key, msg, hashlib.sha256).digest()


def getSignatureKey(key, dateStamp, regionName, serviceName):
    """
    Generate the signing key for AWS V4 requests.

    @param key: The secret key to use.
    @type key: L{bytes}

    @param dateStamp: The UTC date and time, serialized as an AWS date
        stamp.
    @type dateStamp: L{bytes}

    @param regionName: The name of the region.
    @type regionName: L{bytes}

    @param serviceName: The name of the service to which the request
        will be sent.
    @type serviceName: L{bytes}

    @return: The signature.
    @rtype: L{bytes}
    """
    kDate = sign((b'AWS4' + key), dateStamp)
    kRegion = sign(kDate, regionName)
    kService = sign(kRegion, serviceName)
    kSigning = sign(kService, b'aws4_request')
    return kSigning


def makeAMZDate(instant):
    """
    Serialize a L{datetime.datetime} according to the "amz date" format.

    @param instant: A naive UTC L{datetime.datetime} (as returned from
        L{datetime.datetime.utcnow})
    @type instant: L{datetime.datetime}

    @return: The formatted date and time.
    @rtype: L{str} (native string).
    """
    return instant.strftime('%Y%m%dT%H%M%SZ')


def makeDateStamp(instant):
    """
    Serialize a L{datetime.datetime} according to the AWS "date stamp"
    format.

    @param instant: A naive UTC L{datetime.datetime} (as returned from
        L{datetime.datetime.utcnow})
    @type instant: L{datetime.datetime}

    @return: The formatted date and time.
    @rtype: L{str} (native string).
    """
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
    path = urllib.quote(parsed.path)
    canonical_parsed = parsed._replace(path=path,
                                       params='', query='', fragment='')
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
    @type headers_to_sign: A sequence of L{bytes}

    @return: The canonicalized headers.
    @rtype: L{bytes}
    """
    pairs = []
    for name in headers_to_sign:
        if name not in headers:
            continue
        values = headers[name]
        if not isinstance(values, (list, tuple)):
            values = [values]
        comma_values = b','.join(' '.join(line.strip().split())
                                 for value in values
                                 for line in value.splitlines())
        pairs.append((name.lower(), comma_values))

    sorted_pairs = sorted(b'%s:%s' % (name, value)
                          for name, value in sorted(pairs))
    return b'\n'.join(sorted_pairs) + b'\n'


def _make_signed_headers(headers, headers_to_sign):
    """
    Return a semicolon-delimited list of headers to sign.

    @param headers: The request headers.
    @type headers: L{dict}

    @param headers_to_sign: A sequence of header names that should be
        signed.
    @type headers_to_sign: L{bytes}

    @return: The semicolon-delimited list of headers.
    @rtype: L{bytes}
    """
    return b";".join(header.lower() for header in sorted(headers_to_sign)
                     if header in headers)


@attr.s(frozen=True)
class _CanonicalRequest(object):
    """
    A canonicalized request.  See
    U{http://docs.aws.amazon.com/general/latest/gr/sigv4-create-canonical-request.html}

    @ivar method: The HTTP method.
    @type method: L{bytes}

    @ivar canonical_uri: The 'canonical URI'.
        B{N.B.  This should not the full URI!} It should instead be just
        the path and query string.  See L{_make_canonical_uri}.
    @type canonical_uri: L{str}

    @ivar canonical_query_string: The 'canonical query string'.  See
        L{_make_canonical_query_string}.

    @type canonical_headers: The 'canonical headers'.  See
        L{_make_canonical_headers}.
    @ivar canonical_headers: L{bytes}

    @ivar signed_headers: The 'signed headers'.  See
        L{_make_signed_headers}
    @type signed_headers: L{bytes}

    @ivar payload_hash: The SHA256 of the request's body.
    @type payload_hash: L{bytes}
    """
    method = attr.ib()
    canonical_uri = attr.ib()
    canonical_query_string = attr.ib()
    canonical_headers = attr.ib()
    signed_headers = attr.ib()
    payload_hash = attr.ib()

    @classmethod
    def from_request_components(
            cls, method, url, headers, headers_to_sign, payload_hash,
    ):
        """
        Construct a L{_CanonicalRequest} from the provided headers.

        @param method: The HTTP method.
        @type method: L{bytes}

        @param url: The request's URL
        @type url: L{str}

        @param headers: The request's headers.
        @type headers: L{dict}

        @param headers_to_sign: A sequence of header names that should
            be signed.
        @type headers_to_sign: L{bytes}

        @param payload_hash: The hex digest of the sha256 hash of the
            request's body.  If the body is empty, the hex digest of
            the sha256 hash of the empty string.  If the payload hash
            should not be included, C{None}.
        @type payload: L{bytes} or L{NoneType}

        @return: A canonical request
        @rtype: L{_CanonicalRequest}

        @note: If C{payload_hash} is {None} then when the request is
            submitted to AWS it must also include an
            I{x-amz-content-sha256} header set to
            C{b"UNSIGNED-PAYLOAD"}.
        """
        parsed = urlparse.urlparse(url)
        if payload_hash is None:
            # This magic string tells AWS to disregard the payload for
            # purposes of signing.  The x-amz-content-sha256 header
            # sent to AWS in the request must have the exact same
            # value for this to work.
            payload_hash = b"UNSIGNED-PAYLOAD"
        return cls(
            method=method,
            canonical_uri=_make_canonical_uri(parsed),
            canonical_query_string=_make_canonical_query_string(parsed),
            canonical_headers=_make_canonical_headers(headers,
                                                      headers_to_sign),
            signed_headers=_make_signed_headers(headers, headers_to_sign),
            payload_hash=payload_hash,
        )

    @classmethod
    def from_request_components_and_payload(
            cls, method, url, headers, headers_to_sign, payload,
    ):
        """
        Construct a L{_CanonicalRequest} from the provided headers and
        payload.

        @see: L{from_request_components}

        @param payload: The request's payload.
        @type payload: L{bytes}

        @return: A canonical request
        @rtype: L{_CanonicalRequest}
        """
        return cls.from_request_components(
            method=method, url=url, headers=headers,
            headers_to_sign=headers_to_sign,
            payload_hash=hashlib.sha256(payload).hexdigest(),
        )


    def serialize(self):
        """
        Serialize this canonical request to a string.

        @return: The line-delimited serialization of this canonical
            request.
        @rtype: L{str}
        """
        return '\n'.join(attr.astuple(self))

    def hash(self):
        """
        Calculate the SHA256 hash of this canonical request.

        @return: The SHA256 hash of this canonical request's
            serialization.
        @rtype: L{str}
        """
        return hashlib.sha256(self.serialize()).hexdigest()


@attr.s(frozen=True)
class _CredentialScope(object):
    """
    The scope of the AWS credentials.

    @ivar date_stamp: The UTC date and time, in 'date stamp' format.
        See L{makeDateStamp}.
    @type date_stamp: L{str}

    @ivar region: The service region.
    @type region: L{str}

    @ivar service: The name of the service to which the request will
        be made.
    @type: L{str}
    """

    date_stamp = attr.ib()
    region = attr.ib()
    service = attr.ib()

    def serialize(self):
        """
        Serialize this credential scope to a string.

        @return: The slash-delimited credential scope serialization.
        @rtype: L{str}
        """
        return "/".join(attr.astuple(self) + ('aws4_request',))


@attr.s(frozen=True)
class _Credential(object):
    """
    An AWS credential.

    @ivar access_key: The AWS access key.  See
        L{txaws.credentials.AWSCredentials}
    @type access_key: L{str}

    @ivar credential_scope: The credential's scope.  See
        L{_CredentialScope}
    @type access_key: L{str}

    """
    access_key = attr.ib()
    credential_scope = attr.ib()

    def serialize(self):
        """
        Serialize this credential bundle to a string.

        @return: The serialized credential.
        @rtype: L{str}
        """
        return "/".join([self.access_key, self.credential_scope.serialize()])


@attr.s(frozen=True)
class _SignableAWS4HMAC256Token(object):
    """
    A signable AWS4 HMAC 256 token.  The AWS documentation calls the
    serialization of this the "string to sign".

    @ivar amz_date: The UTC date and time in 'date stamp' format.  See
        L{makeDateStamp}.
    @type amz_date: L{str}

    @ivar credential_scope: The scope of this oepration's credentials.
    @type credential_scope: L{_CredentialScope}

    @ivar canonical_request: The canonical request that comprises this
        operation.
    @type canonical_request: L{_CanonicalRequest}
    """

    ALGORITHM = "AWS4-HMAC-SHA256"

    amz_date = attr.ib()
    credential_scope = attr.ib()
    canonical_request = attr.ib()

    def serialize(self):
        """
        Serialize this token to a string.

        @return: The serialization of this token.  This is known in
            the AWS documentation as "the string to sign."
        @rtype: L{str}
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

        @param signing_key: The signing key.  Not just your secret
            key!  See L{getSignatureKey}
        @type: L{str}

        @return: the HMAC-256 signature.
        @rtype: L{str}
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

    @param region: The AWS region name (e.g., C{'us-east-1'}).
    @type region: L{str}

    @param service: The AWS service's name (e.g., C{'s3'}).
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
    @rtype: L{bytes}
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
        b"%s " % (_SignableAWS4HMAC256Token.ALGORITHM,) +
        b", ".join([
            b"Credential=%s" % (v4credential.serialize(),),
            b"SignedHeaders=%s" % (canonical_request.signed_headers,),
            b"Signature=%s" % (signature,),
        ]))
