# Copyright (C) 2010 Jamu Kakar <jkakar@kakar.ca>
# Licenced under the txaws licence available at /LICENSE in the txaws source.

"""A command-line client for discovering how the EC2 API works."""

import os

from txaws.client.discover.command import Command


class OptionError(Exception):
    """
    Raised if insufficient command-line arguments are provided when creating a
    L{Command}.
    """


class UsageError(Exception):
    """Raised if the usage message should be shown."""


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
        if key == "--help":
            raise UsageError("--help specified.")
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
            raise OptionError("'%s' command-line argument is required." % name)

    return options


def get_command(arguments, output=None):
    """Parse C{arguments} and configure a L{Command} instance.

    An access key, secret key, endpoint and action are required.  Additional
    parameters included with the request are passed as parameters to the
    method call.  For example, the following command will invoke the
    C{DescribeRegions} method with a C{RegionName.0} parameter::

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


def main(arguments):
    """
    Entry point parses command-line arguments, runs the specified EC2 API
    method and prints the response to the screen.

    @param arguments: Command-line arguments, typically retrieved from
        C{sys.argv}.
    """
    return 0
