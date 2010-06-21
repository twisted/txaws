# Copyright (C) 2010 Jamu Kakar <jkakar@kakar.ca>
# Licenced under the txaws licence available at /LICENSE in the txaws source.

"""Unit tests for L{get_command}, L{parse_options} and L{main} functions."""

from cStringIO import StringIO
import os
import sys

from txaws.client.discover.entry_point import (
    OptionError, UsageError, get_command, main, parse_options, USAGE_MESSAGE)
from txaws.testing.base import TXAWSTestCase


class ParseOptionsTest(TXAWSTestCase):

    def test_parse_options(self):
        """
        L{parse_options} returns a C{dict} contains options parsed from the
        command-line.
        """
        options = parse_options([
            "txaws-discover", "--key", "key", "--secret", "secret",
            "--endpoint", "endpoint", "--action", "action",
            "--something.else", "something.else"])
        self.assertEqual({"key": "key", "secret": "secret",
                          "endpoint": "endpoint", "action": "action",
                          "something.else": "something.else"},
                         options)

    def test_parse_options_without_options(self):
        """An L{OptionError} is raised if no options are provided."""
        self.assertRaises(OptionError, parse_options, ["txaws-discover"])

    def test_parse_options_with_missing_value(self):
        """
        An L{OptionError} is raised if an option is specified without a value.
        """
        self.assertRaises(OptionError, parse_options,
                          ["txaws-discover", "--key"])

    def test_parse_options_with_missing_option(self):
        """
        An L{OptionError} is raised if a value is specified without an option
        name.
        """
        self.assertRaises(
            OptionError, parse_options,
            ["txaws-discover", "--key", "key", "--secret", "secret",
             "--endpoint", "endpoint", "--action", "action",
             "random-value"])

    def test_parse_options_without_required_arguments(self):
        """
        An access key, access secret, endpoint and action can be specified as
        command-line arguments.  An L{OptionError} is raised if any one of
        these is missing.
        """
        self.assertRaises(OptionError, parse_options,
                          ["txaws-discover", "--secret", "secret",
                           "--endpoint", "endpoint", "--action", "action"])
        self.assertRaises(OptionError, parse_options,
                          ["txaws-discover", "--key", "key",
                           "--endpoint", "endpoint", "--action", "action"])
        self.assertRaises(OptionError, parse_options,
                          ["txaws-discover", "--key", "key",
                           "--secret", "secret", "--action", "action"])
        self.assertRaises(OptionError, parse_options,
                          ["txaws-discover", "--key", "key",
                           "--secret", "secret", "--endpoint", "endpoint"])

    def test_parse_options_gets_key_from_environment(self):
        """
        If the C{AWS_ACCESS_KEY_ID} environment variable is present, it will
        be used if the C{--key} command-line argument isn't specified.
        """
        os.environ["AWS_ACCESS_KEY_ID"] = "key"
        options = parse_options([
            "txaws-discover", "--secret", "secret", "--endpoint", "endpoint",
            "--action", "action"])
        self.assertEqual({"key": "key", "secret": "secret",
                          "endpoint": "endpoint", "action": "action"},
                         options)

    def test_parse_options_prefers_explicit_key(self):
        """
        If an explicit C{--key} command-line argument is specified it will be
        preferred over the value specified in the C{AWS_ACCESS_KEY_ID}
        environment variable.
        """
        os.environ["AWS_ACCESS_KEY_ID"] = "fail"
        options = parse_options([
            "txaws-discover", "--key", "key", "--secret", "secret",
            "--endpoint", "endpoint", "--action", "action"])
        self.assertEqual({"key": "key", "secret": "secret",
                          "endpoint": "endpoint", "action": "action"},
                         options)

    def test_parse_options_gets_secret_from_environment(self):
        """
        If the C{AWS_SECRET_ACCESS_KEY} environment variable is present, it
        will be used if the C{--secret} command-line argument isn't specified.
        """
        os.environ["AWS_SECRET_ACCESS_KEY"] = "secret"
        options = parse_options([
            "txaws-discover", "--key", "key", "--endpoint", "endpoint",
            "--action", "action"])
        self.assertEqual({"key": "key", "secret": "secret",
                          "endpoint": "endpoint", "action": "action"},
                         options)

    def test_parse_options_prefers_explicit_secret(self):
        """
        If an explicit C{--secret} command-line argument is specified it will
        be preferred over the value specified in the C{AWS_SECRET_ACCESS_KEY}
        environment variable.
        """
        os.environ["AWS_SECRET_ACCESS_KEY"] = "fail"
        options = parse_options([
            "txaws-discover", "--key", "key", "--secret", "secret",
            "--endpoint", "endpoint", "--action", "action"])
        self.assertEqual({"key": "key", "secret": "secret",
                          "endpoint": "endpoint", "action": "action"},
                         options)

    def test_parse_options_gets_endpoint_from_environment(self):
        """
        If the C{AWS_ENDPOINT} environment variable is present, it will be
        used if the C{--endpoint} command-line argument isn't specified.
        """
        os.environ["AWS_ENDPOINT"] = "endpoint"
        options = parse_options([
            "txaws-discover", "--key", "key", "--secret", "secret",
            "--action", "action"])
        self.assertEqual({"key": "key", "secret": "secret",
                          "endpoint": "endpoint", "action": "action"},
                         options)

    def test_parse_options_prefers_explicit_endpoint(self):
        """
        If an explicit C{--endpoint} command-line argument is specified it
        will be preferred over the value specified in the C{AWS_ENDPOINT}
        environment variable.
        """
        os.environ["AWS_ENDPOINT"] = "fail"
        options = parse_options([
            "txaws-discover", "--key", "key", "--secret", "secret",
            "--endpoint", "endpoint", "--action", "action"])
        self.assertEqual({"key": "key", "secret": "secret",
                          "endpoint": "endpoint", "action": "action"},
                         options)

    def test_parse_options_raises_usage_error_when_help_specified(self):
        """
        L{UsageError} is raised if C{-h} or C{--help} appears in command-line
        arguments.
        """
        self.assertRaises(UsageError, parse_options,
                          ["txaws-discover", "-h"])
        self.assertRaises(UsageError, parse_options,
                          ["txaws-discover", "--help"])
        self.assertRaises(UsageError, parse_options,
                          ["txaws-discover", "--key", "key",
                           "--secret", "secret", "--endpoint", "endpoint",
                           "--action", "action", "--help"])


class GetCommandTest(TXAWSTestCase):

    def test_get_command_without_arguments(self):
        """An L{OptionError} is raised if no arguments are provided."""
        self.assertRaises(OptionError, get_command, ["txaws-discover"])

    def test_get_command(self):
        """
        An access key, access secret, endpoint and action can be specified as
        command-line arguments.
        """
        command = get_command([
            "txaws-discover", "--key", "key", "--secret", "secret",
            "--endpoint", "endpoint", "--action", "action"])
        self.assertEqual("key", command.key)
        self.assertEqual("secret", command.secret)
        self.assertEqual("endpoint", command.endpoint)
        self.assertEqual("action", command.action)
        self.assertIdentical(sys.stdout, command.output)

    def test_get_command_with_custom_output_stream(self):
        output = StringIO()
        command = get_command([
            "txaws-discover", "--key", "key", "--secret", "secret",
            "--endpoint", "endpoint", "--action", "action"], output)
        self.assertIdentical(output, command.output)

    def test_get_command_without_required_arguments(self):
        """
        An access key, access secret, endpoint and action can be specified as
        command-line arguments.  An L{OptionError} is raised if any one of
        these is missing.
        """
        self.assertRaises(OptionError, get_command,
                          ["txaws-discover", "--secret", "secret",
                           "--endpoint", "endpoint", "--action", "action"])
        self.assertRaises(OptionError, get_command,
                          ["txaws-discover", "--key", "key",
                           "--endpoint", "endpoint", "--action", "action"])
        self.assertRaises(OptionError, get_command,
                          ["txaws-discover", "--key", "key",
                           "--secret", "secret", "--action", "action"])
        self.assertRaises(OptionError, get_command,
                          ["txaws-discover", "--key", "key",
                           "--secret", "secret", "--endpoint", "endpoint"])

    def test_get_command_passes_additional_parameters_to_command(self):
        """
        Command-line parameters beyond C{--key}, C{--secret}, C{--endpoint}
        and C{--action} are passed to the L{Command} in a parameter C{dict}.
        """
        command = get_command([
            "txaws-discover", "--key", "key", "--secret", "secret",
            "--endpoint", "endpoint", "--action", "DescribeRegions",
            "--Region.Name.0", "us-west-1"])
        self.assertEqual({"Region.Name.0": "us-west-1"}, command.parameters)


class MainTest(TXAWSTestCase):

    def test_usage_message(self):
        """
        If a L{UsageError} is raised, the help screen is written to the output
        stream.
        """
        output = StringIO()
        main(["txaws-discover", "--help"], output, True)
        self.assertEqual(USAGE_MESSAGE, output.getvalue())

    def test_error_message(self):
        """
        If an exception is raised, its message is written to the output
        stream.
        """
        output = StringIO()
        main(["txaws-discover"], output, True)
        self.assertEqual(
            "ERROR: The '--key' command-line argument is required.\n",
            output.getvalue())
