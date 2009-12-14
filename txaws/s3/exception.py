# Copyright (c) 2009 Canonical Ltd <duncan.mcgreggor@canonical.com>
# Licenced under the txaws licence available at /LICENSE in the txaws source.

from txaws.exception import AWSError


class S3Error(AWSError):
    """
    A error class providing custom methods on S3 errors.
    """
    def _set_400_error(self, tree):
        if tree.tag.lower() == "error":
            data = self._node_to_dict(tree)
            if data:
                self.errors.append(data)

    def get_error_code(self, *args, **kwargs):
        return super(S3Error, self).get_error_codes(*args, **kwargs)

    def get_error_message(self, *args, **kwargs):
        return super(S3Error, self).get_error_messages(*args, **kwargs)
