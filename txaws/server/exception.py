from twisted.web.error import Error


class APIError(Error):
    """Raised while handling an API request on the server-side."""
