# Copyright (C) 2010 Jamu Kakar <jkakar@kakar.ca>
# Licenced under the txaws licence available at /LICENSE in the txaws source.

"""A command-line client for discovering how the EC2 API works."""

import sys


class ConfigurationError(Exception):
    """
    Raised if insufficient command-line arguments are provided when creating a
    L{Command}.
    """


def parse_options(arguments):
    options = {}
    arguments = arguments[1:]
    while arguments:
        key = arguments.pop(0)
        if key.startswith("--"):
            key = key[2:]
            value = arguments.pop(0)
            options[key] = value
    return options


def get_command(arguments):
    """Parse C{arguments} and configure a L{Command} instance.

    An access key, secret key, endpoint and action are required.  Additional
    parameters included with the request are passed as parameters to the
    method call.  For example, the following command will invoke the
    C{DescribeRegions} method with a C{RegionName.0} parameter::

      txaws-discover --key KEY --secret SECRET --endpoint URL \
                     --action DescribeRegions --RegionName.0 us-west-1

    @param arguments: The command-line arguments to parse.
    @return: A L{Command} instance configured to make an EC2 API call.
    @raises ConfigurationError: Raised if C{arguments} can't be used to create
        a L{Command} object.
    """
    if len(arguments) < 2:
        raise ConfigurationError("Need to provide command-line arguments.")
    options = parse_options(arguments)
    return Command(options["key"], options["secret"], options["endpoint"],
                   options["action"], [])


class Command(object):
    """
    A representation of an EC2 API method call that can make a request and
    display the response received from the backend cloud.
    """

    def __init__(self, key, secret, endpoint, action, parameters, output=None):
        self.key = key
        self.secret = secret
        self.endpoint = endpoint
        self.action = action
        self.parameters = parameters
        if output is None:
            output = sys.stdout
        self.output = output

    def run(self):
        pass


def main(arguments):
    """
    Entry point parses command-line arguments, runs the specified EC2 API
    method and prints the response to the screen.

    @param arguments: Command-line arguments, typically retrieved from
        C{sys.argv}.
    """
    return 0
