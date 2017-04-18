# Copyright (C) 2009 Robert Collins <robertc@robertcollins.net>
# Licenced under the txaws licence available at /LICENSE in the txaws source.

from textwrap import dedent

from twisted.trial.unittest import TestCase

from txaws.credentials import (
    AWSCredentials,
    ENV_ACCESS_KEY,
    ENV_PROFILE,
    ENV_SECRET_KEY,
    ENV_SHARED_CREDENTIALS_FILE,
)
from txaws.exception import CredentialsNotFoundError


class CredentialsTestCase(TestCase):

    def test_no_access_key(self):
        # Without anything in os.environ or in the shared credentials file,
        # AWSService() blows up
        with self.assertRaises(CredentialsNotFoundError):
            AWSCredentials(environ={ENV_SECRET_KEY: "bar"})

    def test_no_secret_key(self):
        # Without anything in os.environ or in the shared credentials file,
        # AWSService() blows up
        with self.assertRaises(CredentialsNotFoundError):
            AWSCredentials(environ={ENV_ACCESS_KEY: "foo"})

    def test_errors_are_valueerrors_for_backwards_compat(self):
        # For unfortunate backwards compatibility reasons, we raise an
        # exception that ValueError will catch
        with self.assertRaises(ValueError):
            AWSCredentials(environ={ENV_ACCESS_KEY: "foo"})

    def test_found_values_used(self):
        service = AWSCredentials(
            environ={ENV_ACCESS_KEY: "foo", ENV_SECRET_KEY: "bar"},
        )
        self.assertEqual(
            service, AWSCredentials(access_key="foo", secret_key="bar"),
        )

    def test_explicit_access_key(self):
        service = AWSCredentials(
            access_key="foo",
            environ={ENV_SECRET_KEY: "bar"},
        )
        self.assertEqual(
            service, AWSCredentials(access_key="foo", secret_key="bar"),
        )

    def test_explicit_secret_key(self):
        service = AWSCredentials(
            secret_key="bar",
            environ={ENV_ACCESS_KEY: "foo"},
        )
        self.assertEqual(
            service, AWSCredentials(access_key="foo", secret_key="bar"),
        )

    def test_explicit_shared_credentials_file(self):
        with open(self.mktemp(), "w") as credentials_file:
            credentials_file.write(
                dedent(
                    """
                    [default]
                    aws_access_key_id = foo
                    aws_secret_access_key = bar
                    """
                ),
            )
        service = AWSCredentials(
            environ={ENV_SHARED_CREDENTIALS_FILE: credentials_file.name},
        )
        self.assertEqual(
            service, AWSCredentials(access_key="foo", secret_key="bar"),
        )

    def test_explicit_shared_credentials_file_overridden(self):
        with open(self.mktemp(), "w") as credentials_file:
            credentials_file.write(
                dedent(
                    """
                    [default]
                    aws_access_key_id = foo
                    aws_secret_access_key = bar
                    """
                ),
            )

        service = AWSCredentials(
            environ={
                ENV_SHARED_CREDENTIALS_FILE: credentials_file.name,
                ENV_ACCESS_KEY: "baz",
                ENV_SECRET_KEY: "quux",
            },
        )
        self.assertEqual(
            service, AWSCredentials(access_key="baz", secret_key="quux"),
        )

    def test_non_default_profile(self):
        with open(self.mktemp(), "w") as credentials_file:
            credentials_file.write(
                dedent(
                    """
                    [another]
                    aws_access_key_id = foo
                    aws_secret_access_key = bar
                    """
                ),
            )

        service = AWSCredentials(
            environ={
                ENV_SHARED_CREDENTIALS_FILE: credentials_file.name,
                ENV_PROFILE: "another",
            },
        )
        self.assertEqual(
            service, AWSCredentials(access_key="foo", secret_key="bar"),
        )

    def test_no_such_profile(self):
        with open(self.mktemp(), "w") as credentials_file:
            credentials_file.write(
                dedent(
                    """
                    [default]
                    aws_access_key_id = foo
                    aws_secret_access_key = bar
                    """
                ),
            )

        with self.assertRaises(CredentialsNotFoundError) as e:
            AWSCredentials(
                environ={
                    ENV_SHARED_CREDENTIALS_FILE: credentials_file.name,
                    ENV_PROFILE: "another",
                },
            )

        self.assertIn("'another'", str(e.exception))

    def test_missing_option(self):
        with open(self.mktemp(), "w") as credentials_file:
            credentials_file.write(
                dedent(
                    """
                    [default]
                    aws_access_key_id = foo
                    """
                ),
            )

        with self.assertRaises(CredentialsNotFoundError) as e:
            AWSCredentials(
                environ={ENV_SHARED_CREDENTIALS_FILE: credentials_file.name},
            )

        self.assertIn("'aws_secret_access_key'", str(e.exception))
