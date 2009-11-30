# Copyright (c) 2009 Canonical Ltd <duncan.mcgreggor@canonical.com>
# Licenced under the txaws licence available at /LICENSE in the txaws source.

from twisted.web.error import Error


class AWSError(Error):
    """
    A base class for txAWS errors.
    """


class AWSResponseParseError(Exception):
    """
    txAWS was unable to parse the server response.
    """
