# Copyright (C) 2009 Robert Collins <robertc@robertcollins.net>
# Licenced under the txaws licence available at /LICENSE in the txaws source.

"""Credentials for accessing AWS services."""

import os

from txaws.util import *


__all__ = ['AWSCredentials']


class AWSCredentials(object):

    def __init__(self, access_key=None, secret_key=None):
        """Create an AWSCredentials object.

        :param access_key: The access key to use. If None the environment
            variable AWS_ACCESS_KEY_ID is consulted.
        :param secret_key: The secret key to use. If None the environment
            variable AWS_SECRET_ACCESS_KEY is consulted.
        """
        self.secret_key = secret_key
        if self.secret_key is None:
            self.secret_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
        if self.secret_key is None:
            raise ValueError('Could not find AWS_SECRET_ACCESS_KEY')
        self.access_key = access_key
        if self.access_key is None:
            self.access_key = os.environ.get('AWS_ACCESS_KEY_ID')
        if self.access_key is None:
            raise ValueError('Could not find AWS_ACCESS_KEY_ID')

    def sign(self, bytes):
        """Sign some bytes."""
        return hmac_sha1(self.secret_key, bytes)
