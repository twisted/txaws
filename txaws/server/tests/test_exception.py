from unittest import TestCase

from txaws.server.exception import APIError


class APIErrorTest(TestCase):

    def test_with_no_parameters(self):
        """
        The L{APIError} constructor must be passed either a code/message pair
        or a full response payload.
        """
        self.assertRaises(RuntimeError, APIError, 400)

    def test_with_response_and_code(self):
        """
        If the L{APIError} constructor is passed a full response payload, it
        can't be passed an error code.
        """
        self.assertRaises(RuntimeError, APIError, 400, code="FooBar",
                          response="foo bar")

    def test_with_response_and_message(self):
        """
        If the L{APIError} constructor is passed a full response payload, it
        can't be passed an error code.
        """
        self.assertRaises(RuntimeError, APIError, 400, message="Foo Bar",
                          response="foo bar")

    def test_with_code_and_no_message(self):
        """
        If the L{APIError} constructor is passed an error code, it must be
        passed an error message as well.
        """
        self.assertRaises(RuntimeError, APIError, 400, code="FooBar")

    def test_with_message_and_no_code(self):
        """
        If the L{APIError} constructor is passed an error message, it must be
        passed an error code as well.
        """
        self.assertRaises(RuntimeError, APIError, 400, message="Foo Bar")

    def test_with_string_status(self):
        """
        The L{APIError} constructor can be passed a C{str} as status code, and
        it will be converted to C{intp}.
        """
        error = APIError("200", response="noes")
        self.assertEqual(200, error.status)
