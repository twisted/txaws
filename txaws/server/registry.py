from txaws.server.exception import APIError


class Registry(object):
    """Register API L{Method}s. for handling specific actions and versions"""

    def __init__(self):
        self._by_action = {}

    def add(self, method_class, action, version=None):
        """Add a method class to the regitry.

        @param method_class: The method class to add
        @param action: The action that the method class can handle
        @param version: The version that the method class can handle
        """
        by_version = self._by_action.setdefault(action, {})
        if version in by_version:
            raise RuntimeError("A method was already registered for action"
                               " %s in version %s" % (action, version))
        by_version[version] = method_class

    def check(self, action, version=None):
        """Check if the given action is supported in the given version.

        @raises APIError: If there's no method class registered for handling
            the given action or version.
        """
        if action not in self._by_action:
            raise APIError(400, "InvalidAction", "The action %s is not valid "
                           "for this web service." % action)
        by_version = self._by_action[action]
        if None not in by_version:
            # There's no catch-all method, let's try the version-specific one
            if version not in by_version:
                raise APIError(400, "InvalidVersion", "Invalid API version.")

    def get(self, action, version=None):
        """Get the method class handing the given action and version."""
        by_version = self._by_action[action]
        if version in by_version:
            return by_version[version]
        else:
            return by_version[None]

    def scan(self, module, onerror=None):
        """Scan the given module object for L{Method}s and register them."""
        from venusian import Scanner
        scanner = Scanner(registry=self)
        scanner.scan(module, onerror=onerror, categories=["method"])
