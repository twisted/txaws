# Copyright (C) 2009 Duncan McGreggor <duncan@canonical.com>
# Licenced under the txaws licence available at /LICENSE in the txaws source.

from txaws.service import AWSService


S3_HOST = "s3.amazonaws.com"


class S3Service(AWSService):
    """
    This service uses the standard S3 host defined with S3_HOST by default. To
    override this behaviour, simply pass the desired value in the "host"
    keyword parameter.

    For more details, see txaws.service.AWSService.
    """
    default_host = S3_HOST
    default_schema = "https"
