# Copyright (C) 2010 Jamu Kakar <jkakar@kakar.ca>
# Licenced under the txaws licence available at /LICENSE in the txaws source.

"""
A L{Command} object makes an arbitrary EC2 API method call and displays the
response received from the backend cloud.
"""

import sys


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
