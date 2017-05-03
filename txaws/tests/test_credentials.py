# Copyright (C) 2009 Robert Collins <robertc@robertcollins.net>
# Licenced under the txaws licence available at /LICENSE in the txaws source.

from textwrap import dedent

from twisted.python.filepath import FilePath
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
    def setUp(self):
        self.credentials_path = FilePath(self.mktemp())

    def environ(self, items):
        """
        Create an environment pointing at a credentials file that belongs to this
        test method run.

        @param items: An environment dictionary.
        @type items: L{dict}

        @return: An environment dictionary like C{items} but with an item
            added or changed so that C{self.credentials_path} will be used as
            the credentials file instead of the default.
        @rtype: L{dict}
        """
        items = items.copy()
        items[ENV_SHARED_CREDENTIALS_FILE] = self.credentials_path.path
        return items

    def credentials(self, *a, **kw):
        """
        Construct an L{AWSCredentials} instance with the given parameters but
        pointing at C{self.credentials_path} instead of the default
        credentials file.
        """
        kw["environ"] = self.environ(kw.get("environ", {}))
        return AWSCredentials(*a, **kw)

    def test_no_access_key(self):
        # Without anything in os.environ or in the shared credentials file,
        # AWSService() blows up
        with self.assertRaises(CredentialsNotFoundError):
            self.credentials(environ=self.environ({ENV_SECRET_KEY: "bar"}))

    def test_no_secret_key(self):
        # Without anything in os.environ or in the shared credentials file,
        # AWSService() blows up
        with self.assertRaises(CredentialsNotFoundError):
            self.credentials(environ={ENV_ACCESS_KEY: "foo"})

    def test_errors_are_valueerrors_for_backwards_compat(self):
        # For unfortunate backwards compatibility reasons, we raise an
        # exception that ValueError will catch
        with self.assertRaises(ValueError):
            self.credentials(environ={ENV_ACCESS_KEY: "foo"})

    def test_found_values_used(self):
        service = AWSCredentials(
            environ={ENV_ACCESS_KEY: "foo", ENV_SECRET_KEY: "bar"},
        )
        self.assertEqual(
            service, AWSCredentials(access_key="foo", secret_key="bar"),
        )

    def test_explicit_access_key(self):
        service = self.credentials(
            access_key="foo",
            environ={ENV_SECRET_KEY: "bar"},
        )
        self.assertEqual(
            service, AWSCredentials(access_key="foo", secret_key="bar"),
        )

    def test_explicit_secret_key(self):
        service = self.credentials(
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
        # Construct AWSCredentials here instead of using the self.credentials
        # helper because we're interested in testing exactly what happens when
        # this env var is set.
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

        # See comment in test_explicit_shared_credentials_file
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

        # See comment in test_explicit_shared_credentials_file
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
            # See comment in test_explicit_shared_credentials_file
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
            # See comment in test_explicit_shared_credentials_file
            AWSCredentials(
                environ={ENV_SHARED_CREDENTIALS_FILE: credentials_file.name},
            )

        self.assertIn("'aws_secret_access_key'", str(e.exception))
