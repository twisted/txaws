# Copyright (C) 2009 Duncan McGreggor <duncan@canonical.com>
# Licenced under the txaws licence available at /LICENSE in the txaws source.

from txaws.service import AWSService


US_EC2_HOST = "us-east-1.ec2.amazonaws.com"
EU_EC2_HOST = "eu-west-1.ec2.amazonaws.com"


class EC2Service(AWSService):
    """
    This service uses the EC2 host defined in US_EC2_HOST by default. To
    override this behaviour, simply pass the desired value in the "host"
    keyword parameter.

    For more details, see txaws.service.AWSService.
    """
    default_host = US_EC2_HOST
