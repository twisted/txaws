from venusian import attach, Scanner

from txaws.server.exception import APIError


def api(method_class):
    """Decorator to use to mark an API method.

    When invoking L{Registry.scan} the classes marked with this decorator
    will be added to the registry.

    @param method_class: The L{Method} class to register.
    """

    def callback(scanner, name, method_class):
        actions = method_class.actions or [name]
        versions = method_class.versions or [None]
        for action in actions:
            for version in versions:
                scanner.registry.add(method_class,
                                     action=action,
                                     version=version)

    attach(method_class, callback)
    return method_class


class Method(object):
    """Handle a single HTTP request to an API resource.

    @cvar actions: List of actions that the Method can handle, if C{None}
        the class name will be used as only supported action.
    @cvar versions: List of versions that the Method can handle, if C{None}
        all versions will be supported.
    """
    actions = None
    versions = None

    def invoke(self, call):
        """Invoke this method for executing the given C{call}."""
        raise NotImplemented("Sub-classes have to implement the invoke method")


class Registry(object):
    """Register API L{Method}s. for handling specific actions and versions"""

    def __init__(self):
        self._actions = {}

    def add(self, method_class, action, version):
        """Add a method class to the regitry.

        @param method_class: The method class to add
        @param action: The action that the method class can handle
        @param version: The version that the method class can handle
        """
        action_versions = self._actions.setdefault(action, {})
        if version in action_versions:
            raise RuntimeError("A method was already registered for action"
                                   " %s in version %s" % (action, version))
        action_versions[version] = method_class

    def check(self, action, version):
        """Check if the given action is supported in the given version.

        @raises APIError: If there's no method class registered for handling
            the given action or version.
        """
        if action not in self._actions:
            raise APIError(400, "InvalidAction", "The action %s is not valid "
                           "for this web service." % action)
        if None not in self._actions[action]:
            # There's no catch-all method, let's try the version-specific one
            if version not in self._actions[action]:
                raise APIError(400, "InvalidVersion", "Invalid API version.")

    def get(self, action, version):
        """Get the method class handing the given action and version."""
        if version in self._actions[action]:
            return self._actions[action][version]
        else:
            return self._actions[action][None]

    def scan(self, module):
        """Scan the given module object for L{Method}s and register them."""
        scanner = Scanner(registry=self)
        scanner.scan(module)
