# Licenced under the txaws licence available at /LICENSE in the txaws source.

"""
Integration tests for the EC2 client(s).
"""

from twisted.trial.unittest import TestCase
from twisted.internet.defer import inlineCallbacks

from txaws.ec2.model import ConsoleOutput

def ec2_integration_tests(get_client):
    class EC2IntegrationTests(TestCase):

        @inlineCallbacks
        def test_get_console_output(self):
            """
            An EC2 instance's console output can be retrieved using
            ``get_console_output``.
            """
            client = get_client(self)
            # TODO: Make it so this test could possibly pass against the real
            # implementation.
            output = yield client.get_console_output(u"i-abcdefghijklmnop")
            self.assertIsInstance(output, ConsoleOutput)

    return EC2IntegrationTests
