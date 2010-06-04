# Copyright (C) 2010 Jamu Kakar <jkakar@kakar.ca>
# Licenced under the txaws licence available at /LICENSE in the txaws source.

"""Unit tests for L{Command}, L{get_command} and L{main}."""

import sys

from txaws.client.discover.discover import ConfigurationError, get_command
from txaws.testing.base import TXAWSTestCase


class GetCommandTest(TXAWSTestCase):

    def test_get_command_without_arguments(self):
        """A L{ConfigurationError} is raised if no arguments are provided."""
        self.assertRaises(ConfigurationError, get_command, ["txaws-discover"])

    def test_get_command(self):
        """
        An access key, access secret, endpoint and action can be specified as
        command-line arguments.
        """
        command = get_command(["txaws-discover", "--key", "key", "--secret",
                               "secret", "--endpoint", "endpoint", "--action",
                               "action"])
        self.assertEqual("key", command.key)
        self.assertEqual("secret", command.secret)
        self.assertEqual("endpoint", command.endpoint)
        self.assertEqual("action", command.action)
        self.assertEqual([], command.parameters)
        self.assertIdentical(sys.stdout, command.output)

