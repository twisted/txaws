from twisted.trial.unittest import TestCase

from txaws.server.method import Method
from txaws.server.registry import Registry
from txaws.server.exception import APIError

from txaws.server.tests.fixtures import (
    has_venusian, importerror, amodule)
from txaws.server.tests.fixtures.amodule import TestMethod
from txaws.server.tests.fixtures.importerror.amodule import (
    TestMethod as testmethod)


class RegistryTest(TestCase):

    def setUp(self):
        super(RegistryTest, self).setUp()
        self.registry = Registry()

    def test_add(self):
        """
        L{MehtodRegistry.add} registers a method class for the given action
        and version.
        """
        self.registry.add(TestMethod, "test", "1.0")
        self.registry.add(TestMethod, "test", "2.0")
        self.registry.check("test", "1.0")
        self.registry.check("test", "2.0")
        self.assertIdentical(TestMethod, self.registry.get("test", "1.0"))
        self.assertIdentical(TestMethod, self.registry.get("test", "2.0"))

    def test_add_duplicate_method(self):
        """
        L{MehtodRegistry.add} fails if a method class for the given action
        and version was already registered.
        """

        class TestMethod2(Method):
            pass

        self.registry.add(TestMethod, "test", "1.0")
        self.assertRaises(RuntimeError, self.registry.add, TestMethod2,
                          "test", "1.0")

    def test_get(self):
        """
        L{MehtodRegistry.get} returns the method class registered for the
        given action and version.
        """

        class TestMethod2(Method):
            pass

        self.registry.add(TestMethod, "test", "1.0")
        self.registry.add(TestMethod, "test", "2.0")
        self.registry.add(TestMethod2, "test", "3.0")
        self.assertIdentical(TestMethod, self.registry.get("test", "1.0"))
        self.assertIdentical(TestMethod, self.registry.get("test", "2.0"))
        self.assertIdentical(TestMethod2, self.registry.get("test", "3.0"))

    def test_check_with_missing_action(self):
        """
        L{MehtodRegistry.get} fails if the given action is not registered.
        """
        error = self.assertRaises(APIError, self.registry.check, "boom", "1.0")
        self.assertEqual(400, error.status)
        self.assertEqual("InvalidAction", error.code)
        self.assertEqual("The action boom is not valid for this web service.",
                         error.message)

    def test_check_with_missing_version(self):
        """
        L{MehtodRegistry.get} fails if the given action is not registered.
        """
        self.registry.add(TestMethod, "test", "1.0")
        error = self.assertRaises(APIError, self.registry.check, "test", "2.0")
        self.assertEqual(400, error.status)
        self.assertEqual("InvalidVersion", error.code)
        self.assertEqual("Invalid API version.", error.message)

    def test_scan(self):
        """
        L{MehtodRegistry.scan} registers the L{Method}s decorated with L{api}.
        """
        self.registry.scan(amodule)
        self.assertIdentical(TestMethod, self.registry.get("TestMethod", None))

    def test_scan_raises_error_on_importerror(self):
        """
        L{MethodRegistry.scan} raises an error by default when an error happens
        and there is no onerror callback is passed.
        """
        self.assertRaises(ImportError, self.registry.scan, importerror)

    def test_scan_swallows_with_onerror(self):
        """
        L{MethodRegistry.scan} accepts an onerror callback that can be used to
        deal with scanning errors.
        """
        swallowed = []
        def swallow(error):
            swallowed.append(error)

        self.registry.scan(importerror, onerror=swallow)
        self.assertEqual(1, len(swallowed))
        self.assertEqual(testmethod, self.registry.get("TestMethod"))

    if not has_venusian:
        test_scan.skip = "venusian module not available"
        test_scan_raises_error_on_importerror.skip = "venusian module not "
        "available"
        test_scan_swallows_with_onerror.skip = "venusian module not available"
