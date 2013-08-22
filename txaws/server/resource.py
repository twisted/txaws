from datetime import datetime, timedelta
from uuid import uuid4
from dateutil.tz import tzutc

from twisted.python import log
from twisted.python.reflect import safe_str
from twisted.internet.defer import maybeDeferred
from twisted.web.resource import Resource
from twisted.web.server import NOT_DONE_YET

from txaws.ec2.client import Signature
from txaws.service import AWSServiceEndpoint
from txaws.credentials import AWSCredentials
from txaws.server.schema import (
    Schema, Unicode, Integer, RawStr, Date)
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
        RawStr("Version", optional=True),
        Unicode("SignatureMethod",
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
            # Prevent browsers from trying to guess a different content type.
            request.setHeader("X-Content-Type-Options", "nosniff")
            request.write(response)
            request.finish()
            return response

        def write_error(failure):
            if failure.check(APIError):
                status = failure.value.status

                # Don't log the stack traces for 4xx responses.
                if status < 400 or status >= 500:
                    log.err(failure)
                else:
                    log.msg("status: %s message: %s" % (
                        status, safe_str(failure.value)))

                body = failure.value.response
                if body is None:
                    body = self.dump_error(failure.value, request)
            else:
                # If the error is a generic one (not an APIError), log the
                # message , but don't send it back to the client, as it could
                # contain sensitive information. Send a generic server error
                # message instead.
                log.err(failure)
                body = "Server error"
                status = 500
            request.setResponseCode(status)
            write_response(body)

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
        return datetime.now(tzutc())

    def get_call_arguments(self, request):
        """
        Get call arguments from a request. Override this if you want to use a
        wire format different from AWS's.

        The return value is a dictionary with three keys: 'transport_args',
        'handler_args', and 'raw_args'.

        The value of 'transport_args' must be a dictionary with the following
        keys:

        - action
        - access_key_id
        - timestamp
        - expires
        - version
        - signature_method
        - signature
        - signature_version

        The value of 'handler_args' should be the application arguments that
        are meant to be passed to the action handler.

        The value of 'raw_args', the unprocessed arguments, are used for
        signature verification. This should be the same dictionary of data that
        the client used to sign the request. Note that this data must not
        contain the signature itself.
        """
        params = dict((k, v[-1]) for k, v in request.args.iteritems())
        args, rest = self.schema.extract(params)
        # Get rid of Signature so it doesn't mess with signature verification
        params.pop("Signature")
        result = {
            "transport_args": {
                "action": args.Action,
                "access_key_id": args.AWSAccessKeyId,
                "timestamp": args.Timestamp,
                "expires": args.Expires,
                "version": args.Version,
                "signature_method": args.SignatureMethod,
                "signature": args.Signature,
                "signature_version": args.SignatureVersion},
            "handler_args": rest,
            "raw_args": params
        }
        return result

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
        call_arguments = self.get_call_arguments(request)
        args = call_arguments["transport_args"]
        rest = call_arguments["handler_args"]
        params = call_arguments["raw_args"]

        self._validate_generic_parameters(args)

        def create_call(principal):
            self._validate_principal(principal, args)
            self._validate_signature(request, principal, args, params)
            return Call(raw_params=rest,
                        principal=principal,
                        action=args["action"],
                        version=args["version"],
                        id=request.id)

        deferred = maybeDeferred(self.get_principal, args["access_key_id"])
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
            if not args["action"] in self.actions:
                raise APIError(400, "InvalidAction", "The action %s is not "
                               "valid for this web service." % args["action"])
        else:
            self.registry.check(args["action"], args["version"])

        if not args["signature_version"] in self.signature_versions:
            raise APIError(403, "InvalidSignature", "SignatureVersion '%s' "
                           "not supported" % args["signature_version"])

        if args["expires"] and args["timestamp"]:
            raise APIError(400, "InvalidParameterCombination",
                           "The parameter Timestamp cannot be used with "
                           "the parameter Expires")
        if args["expires"] and args["expires"] < utc_now:
            raise APIError(400,
                           "RequestExpired",
                           "Request has expired. Expires date is %s" % (
                                args["expires"].strftime(self.time_format)))
        if (args["timestamp"]
            and args["timestamp"] + timedelta(minutes=15) < utc_now):
            raise APIError(400,
                           "RequestExpired",
                           "Request has expired. Timestamp date is %s" % (
                               args["timestamp"].strftime(self.time_format)))

    def _validate_principal(self, principal, args):
        """Validate the principal."""
        if principal is None:
            raise APIError(401, "AuthFailure",
                           "No user with access key '%s'" %
                           args["access_key_id"])

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
        signature = Signature(creds, endpoint, params,
                              signature_method=args["signature_method"],
                              signature_version=args["signature_version"]
                              )
        if signature.compute() != args["signature"]:
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
