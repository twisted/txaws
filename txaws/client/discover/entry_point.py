# Copyright (C) 2010 Jamu Kakar <jkakar@kakar.ca>
# Licenced under the txaws licence available at /LICENSE in the txaws source.

"""A command-line client for discovering how the EC2 API works."""

import os
import sys

from txaws.client.discover.command import Command


class OptionError(Exception):
    """
    Raised if insufficient command-line arguments are provided when creating a
    L{Command}.
    """


class UsageError(Exception):
    """Raised if the usage message should be shown."""


USAGE_MESSAGE = """\
Purpose: Invoke an EC2 API method with arbitrary parameters.
Usage:   txaws-discover [--key KEY] [--secret SECRET] [--endpoint ENDPOINT]
             --action ACTION [PARAMETERS, ...]

Options:
  --key                 The AWS access key to use when making the API request.
  --secret              The AWS secret key to use when making the API request.
  --endpoint            The region endpoint to make the API request against.
  --action              The name of the EC2 API to invoke.
  -h, --help            Show help message.

Description:
  The purpose of this program is to aid discovery of the EC2 API.  It can run
  any EC2 API method, with arbitrary parameters.  The response received from
  the backend cloud is printed to the screen, to show exactly what happened in
  response to the request.  The --key, --secret, --endpoint and --action
  command-line arguments are required.  If AWS_ENDPOINT, AWS_ACCESS_KEY_ID or
  AWS_SECRET_ACCESS_KEY environment variables are defined the corresponding
  options can be omitted and the values defined in the environment variables
  will be used.

  Any additional parameters, beyond those defined above, will be included with
  the request as method parameters.

Examples:
  The following examples omit the --key, --secret and --endpoint command-line
  arguments for brevity.  They must be included unless corresponding values
  are available from the environment.

  Run the DescribeRegions method, without any optional parameters:

    txaws-discover --action DescribeRegions

  Run the DescribeRegions method, with an optional RegionName.0 parameter:

    txaws-discover --action DescribeRegions --RegionName.0 us-west-1
"""


def parse_options(arguments):
    """Parse command line arguments.

    The parsing logic is fairly simple.  It can only parse long-style
    parameters of the form::

      --key value

    Several parameters can be defined in the environment and will be used
    unless explicitly overridden with command-line arguments.  The access key,
    secret and endpoint values will be loaded from C{AWS_ACCESS_KEY_ID},
    C{AWS_SECRET_ACCESS_KEY} and C{AWS_ENDPOINT} environment variables.

    @param arguments: A list of command-line arguments.  The first item is
        expected to be the name of the program being run.
    @raises OptionError: Raised if incorrectly formed command-line arguments
        are specified, or if required command-line arguments are not present.
    @raises UsageError: Raised if C{--help} is present in command-line
        arguments.
    @return: A C{dict} with key/value pairs extracted from the argument list.
    """
    arguments = arguments[1:]
    options = {}
    while arguments:
        key = arguments.pop(0)
        if key in ("-h", "--help"):
            raise UsageError("Help requested.")
        if key.startswith("--"):
            key = key[2:]
            try:
                value = arguments.pop(0)
            except IndexError:
                raise OptionError("'--%s' is missing a value." % key)
            options[key] = value
        else:
            raise OptionError("Encountered unexpected value '%s'." % key)

    default_key = os.environ.get("AWS_ACCESS_KEY_ID")
    if "key" not in options and default_key:
        options["key"] = default_key
    default_secret = os.environ.get("AWS_SECRET_ACCESS_KEY")
    if "secret" not in options and default_secret:
        options["secret"] = default_secret
    default_endpoint = os.environ.get("AWS_ENDPOINT")
    if "endpoint" not in options and default_endpoint:
        options["endpoint"] = default_endpoint
    for name in ("key", "secret", "endpoint", "action"):
        if name not in options:
            raise OptionError(
                "The '--%s' command-line argument is required." % name)

    return options


def get_command(arguments, output=None):
    """Parse C{arguments} and configure a L{Command} instance.

    An access key, secret key, endpoint and action are required.  Additional
    parameters included with the request are passed as parameters to the
    method call.  For example, the following command will create a L{Command}
    object that can invoke the C{DescribeRegions} method with the optional
    C{RegionName.0} parameter included in the request::

      txaws-discover --key KEY --secret SECRET --endpoint URL \
                     --action DescribeRegions --RegionName.0 us-west-1

    @param arguments: The command-line arguments to parse.
    @raises OptionError: Raised if C{arguments} can't be used to create a
        L{Command} object.
    @return: A L{Command} instance configured to make an EC2 API method call.
    """
    options = parse_options(arguments)
    key = options.pop("key")
    secret = options.pop("secret")
    endpoint = options.pop("endpoint")
    action = options.pop("action")
    return Command(key, secret, endpoint, action, options, output)


def main(arguments, output=None, testing_mode=None):
    """
    Entry point parses command-line arguments, runs the specified EC2 API
    method and prints the response to the screen.

    @param arguments: Command-line arguments, typically retrieved from
        C{sys.argv}.
    @param output: Optionally, a stream to write output to.
    @param testing_mode: Optionally, a condition that specifies whether or not
        to run in test mode.  When the value is true a reactor will not be run
        or stopped, to prevent interfering with the test suite.
    """

    def run_command(arguments, output, reactor):
        if output is None:
            output = sys.stdout
        try:
            command = get_command(arguments, output)
        except UsageError:
            print >>output, USAGE_MESSAGE.strip()
            if reactor:
                reactor.callLater(0, reactor.stop)
        except Exception, e:
            print >>output, "ERROR:", str(e)
            if reactor:
                reactor.callLater(0, reactor.stop)
        else:
            deferred = command.run()
            if reactor:
                deferred.addCallback(lambda ignored: reactor.stop())

    if not testing_mode:
        from twisted.internet import reactor
        reactor.callLater(0, run_command, arguments, output, reactor)
        reactor.run()
    else:
        run_command(arguments, output, None)
