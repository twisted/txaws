# Copyright (C) 2009 Robert Collins <robertc@robertcollins.net>
# Licenced under the txaws licence available at /LICENSE in the txaws source.

"""Credentials for accessing AWS services."""

import ConfigParser
import os

import attr

from txaws.exception import CredentialsNotFoundError
from txaws.util import hmac_sha256, hmac_sha1


__all__ = ["AWSCredentials"]


ENV_ACCESS_KEY = "AWS_ACCESS_KEY_ID"
ENV_PROFILE = "AWS_PROFILE"
ENV_SECRET_KEY = "AWS_SECRET_ACCESS_KEY"
ENV_SHARED_CREDENTIALS_FILE = "AWS_SHARED_CREDENTIALS_FILE"


class _CompatCredentialsNotFoundError(CredentialsNotFoundError, ValueError):
    """
    To nudge external code from ValueErrors, we raise a compatibility subclass.
    """


@attr.s(init=False)
class AWSCredentials(object):
    """Create an AWSCredentials object.

    @param access_key: The access key to use. If None the environment variable
        AWS_ACCESS_KEY_ID is consulted.
    @param secret_key: The secret key to use. If None the environment variable
        AWS_SECRET_ACCESS_KEY is consulted.
    @param environ: The environment. If unspecified, L{os.environ} is used.
    @raise CredentialsNotFoundError: No access key or secret was provided, nor
        could they be found in the environment or filesystem.

        I{A L{ValueError} was previously raised in this case, but this
        usage is deprecated and will be removed.}
    """

    access_key = attr.ib()
    secret_key = attr.ib(repr=False)

    def __init__(self, access_key="", secret_key="", environ=os.environ):
        if not access_key:
            access_key = environ.get(ENV_ACCESS_KEY)
            if not access_key:
                access_key, _ = _load_shared_credentials(environ=environ)
        if not secret_key:
            secret_key = environ.get(ENV_SECRET_KEY)
            if not secret_key:
                _, secret_key = _load_shared_credentials(environ=environ)

        self.access_key = access_key
        self.secret_key = secret_key

    def sign(self, bytes, hash_type="sha256"):
        """Sign some bytes."""
        if hash_type == "sha256":
            return hmac_sha256(self.secret_key, bytes)
        elif hash_type == "sha1":
            return hmac_sha1(self.secret_key, bytes)
        else:
            raise RuntimeError("Unsupported hash type: '%s'" % hash_type)


def _load_shared_credentials(environ, profile=None):
    if profile is None:
        profile = environ.get(ENV_PROFILE, "default")

    credentials_path = environ.get(
        ENV_SHARED_CREDENTIALS_FILE,
        os.path.expanduser("~/.aws/credentials"),
    )
    config = ConfigParser.SafeConfigParser()
    if not config.read([credentials_path]):
        raise _CompatCredentialsNotFoundError(
            "Could not find credentials in the environment or filesystem",
        )

    if not config.has_section(profile):
        raise CredentialsNotFoundError("No such profile {!r}".format(profile))

    try:
        return (
            config.get(profile, "aws_access_key_id"),
            config.get(profile, "aws_secret_access_key"),
        )
    except ConfigParser.NoOptionError as error:
        raise CredentialsNotFoundError(
            "Profile {0.section!r} has no {0.option!r}".format(error),
        )
