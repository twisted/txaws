from datetime import datetime, timedelta
from uuid import uuid4
from pytz import UTC

from twisted.python import log
from twisted.internet.defer import maybeDeferred
from twisted.web.resource import Resource
from twisted.web.server import NOT_DONE_YET

from txaws.ec2.client import Signature
from txaws.service import AWSServiceEndpoint
from txaws.credentials import AWSCredentials
from txaws.server.schema import (
    Schema, Unicode, Integer, Enum, RawStr, Date)
from txaws.server.exception import APIError
from txaws.server.call import Call


class QueryAPI(Resource):
    """Base class for  EC2-like query APIs.

    @param registry: The L{Registry} to use to look up L{Method}s for handling
        the API requests.
    @param path: Optionally, the actual resource path the clients are using
        when sending HTTP requests to this API, to take into account when
        validating the signature. This can differ from the one in the HTTP
        request we're processing in case the service sits behind a reverse
        proxy, like Apache. For this works to work you have to make sure
        that 'path + path_of_the_rewritten_request' equals the resource
        path that clients are sending the request to.

    The following class variables must be defined by sub-classes:

    @ivar signature_versions: A list of allowed values for 'SignatureVersion'.
    @cvar content_type: The content type to set the 'Content-Type' header to.
    """
    isLeaf = True
    time_format = "%Y-%m-%dT%H:%M:%SZ"

    schema = Schema(
        Unicode("Action"),
        RawStr("AWSAccessKeyId"),
        Date("Timestamp", optional=True),
        Date("Expires", optional=True),
        Unicode("Version", optional=True),
        Enum("SignatureMethod", {"HmacSHA256": "sha256", "HmacSHA1": "sha1"},
             optional=True, default="HmacSHA256"),
        Unicode("Signature"),
        Integer("SignatureVersion", optional=True, default=2))

    def __init__(self, registry=None, path=None):
        Resource.__init__(self)
        self.path = path
        self.registry = registry

    def get_method(self, call, *args, **kwargs):
        """Return the L{Method} instance to invoke for the given L{Call}.

        @param args: Positional arguments to pass to the method constructor.
        @param kwargs: Keyword arguments to pass to the method constructor.
        """
        method_class = self.registry.get(call.action, call.version)
        method = method_class(*args, **kwargs)
        if not method.is_available():
            raise APIError(400, "InvalidAction", "The action %s is not "
                           "valid for this web service." % call.action)
        else:
            return method

    def get_principal(self, access_key):
        """Return a principal object by access key.

        The returned object must have C{access_key} and C{secret_key}
        attributes and if the authentication succeeds, it will be
        passed to the created L{Call}.
        """
        raise NotImplemented("Must be implemented by subclasses")

    def handle(self, request):
        """Handle an HTTP request for executing an API call.

        This method authenticates the request checking its signature, and then
        calls the C{execute} method, passing it a L{Call} object set with the
        principal for the authenticated user and the generic parameters
        extracted from the request.

        @param request: The L{HTTPRequest} to handle.
        """
        request.id = str(uuid4())
        deferred = maybeDeferred(self._validate, request)
        deferred.addCallback(self.execute)

        def write_response(response):
            request.setHeader("Content-Length", str(len(response)))
            request.setHeader("Content-Type", self.content_type)
            request.write(response)
            request.finish()
            return response

        def write_error(failure):
            log.err(failure)
            if failure.check(APIError):
                status = failure.value.status
                bytes = failure.value.response
                if bytes is None:
                    bytes = self.dump_error(failure.value, request)
            else:
                bytes = str(failure.value)
                status = 500
            request.setResponseCode(status)
            request.write(bytes)
            request.finish()

        deferred.addCallback(write_response)
        deferred.addErrback(write_error)
        return deferred

    def dump_error(self, error, request):
        """Serialize an error generating the response to send to the client.

        @param error: The L{APIError} to format.
        @param request: The request that generated the error.
        """
        raise NotImplementedError("Must be implemented by subclass.")

    def dump_result(self, result):
        """Serialize the result of the method invokation.

        @param result: The L{Method} result to serialize.
        """
        return result

    def authorize(self, method, call):
        """Authorize to invoke the given L{Method} with the given L{Call}."""

    def execute(self, call):
        """Execute an API L{Call}.

        At this point the request has been authenticated and C{call.principal}
        is set with the L{Principal} for the L{User} requesting the call.

        @return: The response to write in the request for the given L{Call}.
        @raises: An L{APIError} in case the execution fails, sporting an error
            message the HTTP status code to return.
        """
        method = self.get_method(call)
        deferred = maybeDeferred(self.authorize, method, call)
        deferred.addCallback(lambda _: method.invoke(call))
        return deferred.addCallback(self.dump_result)

    def get_utc_time(self):
        """Return a C{datetime} object with the current time in UTC."""
        return datetime.now(UTC)

    def _validate(self, request):
        """Validate an L{HTTPRequest} before executing it.

        The following conditions are checked:

        - The request contains all the generic parameters.
        - The action specified in the request is a supported one.
        - The signature mechanism is a supported one.
        - The provided signature matches the one calculated using the locally
          stored secret access key for the user.
        - The signature hasn't expired.

        @return: The validated L{Call}, set with its default arguments and the
           the principal of the accessing L{User}.
        """
        params = dict((k, v[-1]) for k, v in request.args.iteritems())
        args, rest = self.schema.extract(params)

        self._validate_generic_parameters(args)

        def create_call(principal):
            self._validate_principal(principal, args)
            self._validate_signature(request, principal, args, params)
            return Call(raw_params=rest,
                        principal=principal,
                        action=args.Action,
                        version=args.Version,
                        id=request.id)

        deferred = maybeDeferred(self.get_principal, args.AWSAccessKeyId)
        deferred.addCallback(create_call)
        return deferred

    def _validate_generic_parameters(self, args):
        """Validate the generic request parameters.

        @param args: Parsed schema arguments.
        @raises APIError: In the following cases:
            - Action is not included in C{self.actions}
            - SignatureVersion is not included in C{self.signature_versions}
            - Expires and Timestamp are present
            - Expires is before the current time
            - Timestamp is older than 15 minutes.
        """
        utc_now = self.get_utc_time()

        if getattr(self, "actions", None) is not None:
            # Check the deprecated 'actions' attribute
            if not args.Action in self.actions:
                raise APIError(400, "InvalidAction", "The action %s is not "
                               "valid for this web service." % args.Action)
        else:
            self.registry.check(args.Action, args.Version)

        if not args.SignatureVersion in self.signature_versions:
            raise APIError(403, "InvalidSignature", "SignatureVersion '%s' "
                           "not supported" % args.SignatureVersion)

        if args.Expires and args.Timestamp:
            raise APIError(400, "InvalidParameterCombination",
                           "The parameter Timestamp cannot be used with "
                           "the parameter Expires")
        if args.Expires and args.Expires < utc_now:
            raise APIError(400,
                           "RequestExpired",
                           "Request has expired. Expires date is %s" % (
                                args.Expires.strftime(self.time_format)))
        if args.Timestamp and args.Timestamp + timedelta(minutes=15) < utc_now:
            raise APIError(400,
                           "RequestExpired",
                           "Request has expired. Timestamp date is %s" % (
                               args.Timestamp.strftime(self.time_format)))

    def _validate_principal(self, principal, args):
        """Validate the principal."""
        if principal is None:
            raise APIError(401, "AuthFailure",
                           "No user with access key '%s'" %
                           args.AWSAccessKeyId)

    def _validate_signature(self, request, principal, args, params):
        """Validate the signature."""
        creds = AWSCredentials(principal.access_key, principal.secret_key)
        endpoint = AWSServiceEndpoint()
        endpoint.set_method(request.method)
        endpoint.set_canonical_host(request.getHeader("Host"))
        path = request.path
        if self.path is not None:
            path = "%s/%s" % (self.path.rstrip("/"), path.lstrip("/"))
        endpoint.set_path(path)
        params.pop("Signature")
        signature = Signature(creds, endpoint, params)
        if signature.compute() != args.Signature:
            raise APIError(403, "SignatureDoesNotMatch",
                           "The request signature we calculated does not "
                           "match the signature you provided. Check your "
                           "key and signing method.")

    def get_status_text(self):
        """Get the text to return when a status check is made."""
        return "Query API Service"

    def render_GET(self, request):
        """Handle a GET request."""
        if not request.args:
            request.setHeader("Content-Type", "text/plain")
            return self.get_status_text()
        else:
            self.handle(request)
            return NOT_DONE_YET

    render_POST = render_GET
