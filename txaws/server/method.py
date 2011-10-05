def method(method_class):
    """Decorator to use to mark an API method.

    When invoking L{Registry.scan} the classes marked with this decorator
    will be added to the registry.

    @param method_class: The L{Method} class to register.
    """

    def callback(scanner, name, method_class):
        if method_class.actions is not None:
            actions = method_class.actions
        else:
            actions = [name]

        if method_class.versions is not None:
            versions = method_class.versions
        else:
            versions = [None]

        for action in actions:
            for version in versions:
                scanner.registry.add(method_class,
                                     action=action,
                                     version=version)

    from venusian import attach
    attach(method_class, callback, category="method")
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

    def is_available(self):
        """Return a boolean indicating wether this method is available.

        Override this to dynamically decide at run-time whether specific
        methods are available or not.
        """
        return True
