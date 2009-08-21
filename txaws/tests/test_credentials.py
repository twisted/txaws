# Copyright (C) 2009 Robert Collins <robertc@robertcollins.net>
# Licenced under the txaws licence available at /LICENSE in the txaws source.

import os

from twisted.trial.unittest import TestCase

from txaws.credentials import AWSCredentials
from txaws.tests import TXAWSTestCase


class TestCredentials(TXAWSTestCase):

    def test_no_access_errors(self):
        # Without anything in os.environ, AWSCredentials() blows up
        os.environ['AWS_SECRET_ACCESS_KEY'] = 'foo'
        self.assertRaises(Exception, AWSCredentials)

    def test_no_secret_errors(self):
        # Without anything in os.environ, AWSCredentials() blows up
        os.environ['AWS_ACCESS_KEY_ID'] = 'bar'
        self.assertRaises(Exception, AWSCredentials)

    def test_found_values_used(self):
        os.environ['AWS_SECRET_ACCESS_KEY'] = 'foo'
        os.environ['AWS_ACCESS_KEY_ID'] = 'bar'
        creds = AWSCredentials()
        self.assertEqual('foo', creds.secret_key)
        self.assertEqual('bar', creds.access_key)

    def test_explicit_access_key(self):
        os.environ['AWS_SECRET_ACCESS_KEY'] = 'foo'
        creds = AWSCredentials(access_key='bar')
        self.assertEqual('foo', creds.secret_key)
        self.assertEqual('bar', creds.access_key)

    def test_explicit_secret_key(self):
        os.environ['AWS_ACCESS_KEY_ID'] = 'bar'
        creds = AWSCredentials(secret_key='foo')
        self.assertEqual('foo', creds.secret_key)
        self.assertEqual('bar', creds.access_key)
