# Copyright (c) 2009 Canonical Ltd <duncan.mcgreggor@canonical.com>
# Licenced under the txaws licence available at /LICENSE in the txaws source.

from txaws.exception import AWSError


class EC2Error(AWSError):
    """
    A error class providing custom methods on EC2 errors.
    """
    def _set_400_error(self, tree):
        errors_node = tree.find(".//Errors")
        if errors_node is not None:
            for error in errors_node:
                data = self._node_to_dict(error)
                if data:
                    self.errors.append(data)



