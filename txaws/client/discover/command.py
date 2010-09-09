# Copyright (C) 2010 Jamu Kakar <jkakar@kakar.ca>
# Licenced under the txaws licence available at /LICENSE in the txaws source.

"""
A L{Command} object makes an arbitrary EC2 API method call and displays the
response received from the backend cloud.
"""

import sys

from txaws.ec2.client import Query
from txaws.exception import AWSError
from txaws.service import AWSServiceRegion


class Command(object):
    """
    An EC2 API method call command that can make a request and display the
    response received from the backend cloud.

    @param key: The AWS access key ID to use when making the method call.
    @param secret: The AWS secret key to sign the method call with.
    @param endpoint: The URL of the cloud to invoke the method on.
    @param parameters: A C{dict} with parameters to include with the method
        call.
    @param output: Optionally, a stream to write output to.  Defaults to
        C{sys.stdout}.
    @param query_factory: Optionally, a factory to create the L{Query} object
        used to invoke the method.  Defaults to returning a L{Query} instance.
    """

    def __init__(self, key, secret, endpoint, action, parameters, output=None,
                 query_factory=None):
        self.key = key
        self.secret = secret
        self.endpoint = endpoint
        self.action = action
        self.parameters = parameters
        if output is None:
            output = sys.stdout
        self.output = output
        if query_factory is None:
            query_factory = Query
        self.query_factory = query_factory

    def run(self):
        """
        Run the configured method and write the HTTP response status and text
        to the output stream.
        """
        region = AWSServiceRegion(access_key=self.key, secret_key=self.secret,
                                  uri=self.endpoint)
        query = self.query_factory(action=self.action, creds=region.creds,
                                   endpoint=region.ec2_endpoint,
                                   other_params=self.parameters)

        def write_response(response):
            print >>self.output, "URL: %s" % query.client.url
            print >>self.output
            print >>self.output, "HTTP status code: %s" % query.client.status
            print >>self.output
            print >>self.output, response

        def write_error(failure):
            if failure.check(AWSError):
                message = failure.value.original
            else:
                message = failure.getErrorMessage()
                if message.startswith("Error Message: "):
                    message = message[len("Error Message: "):]

            print >>self.output, "URL: %s" % query.client.url
            print >>self.output
            print >>self.output, "HTTP status code: %s" % query.client.status
            print >>self.output
            print >>self.output, message

        deferred = query.submit()
        deferred.addCallback(write_response)
        deferred.addErrback(write_error)
        return deferred
