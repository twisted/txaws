# Copyright (C) 2009 Duncan McGreggor <duncan@canonical.com>
# Copyright (C) 2009 Robert Collins <robertc@robertcollins.net>
# Copyright (C) 2012 New Dream Network, LLC (DreamHost)
# Licenced under the txaws licence available at /LICENSE in the txaws source.

__all__ = ["REGION_US", "REGION_EU", "EC2_US_EAST", "EC2_US_WEST",
"EC2_ASIA_PACIFIC", "EC2_EU_WEST", "EC2_SOUTH_AMERICA_EAST", "EC2_ALL_REGIONS"]


# These old EC2 variable names are maintained for backwards compatibility.
REGION_US = "US"
REGION_EU = "EU"
EC2_ENDPOINT_US = "https://us-east-1.ec2.amazonaws.com/"
EC2_ENDPOINT_EU = "https://eu-west-1.ec2.amazonaws.com/"

# These are the new EC2 variables.
EC2_US_EAST = [
    {"region": "US East (Northern Virginia) Region",
     "endpoint": "https://ec2.us-east-1.amazonaws.com"}]
EC2_US_WEST = [
    {"region": "US West (Oregon) Region",
     "endpoint": "https://ec2.us-west-2.amazonaws.com"},
    {"region": "US West (Northern California) Region",
     "endpoint": "https://ec2.us-west-1.amazonaws.com"}]
EC2_US = EC2_US_EAST + EC2_US_WEST
EC2_ASIA_PACIFIC = [
    {"region": "Asia Pacific (Singapore) Region",
     "endpoint": "https://ec2.ap-southeast-1.amazonaws.com"},
    {"region": "Asia Pacific (Tokyo) Region",
     "endpoint": "https://ec2.ap-northeast-1.amazonaws.com"}]
EC2_EU_WEST = [
    {"region": "EU (Ireland) Region",
     "endpoint": "https://ec2.eu-west-1.amazonaws.com"}]
EC2_EU = EC2_EU_WEST
EC2_SOUTH_AMERICA_EAST = [
    {"region": "South America (Sao Paulo) Region",
     "endpoint": "https://ec2.sa-east-1.amazonaws.com"}]
EC2_SOUTH_AMERICA = EC2_SOUTH_AMERICA_EAST
EC2_ALL_REGIONS = EC2_US + EC2_ASIA_PACIFIC + EC2_EU + EC2_SOUTH_AMERICA

# This old S3 variable is maintained for backwards compatibility.
S3_ENDPOINT = "https://s3.amazonaws.com/"

# These are the new S3 variables.
S3_US_DEFAULT = [
    {"region": "US Standard *",
     "endpoint": "https://s3.amazonaws.com"}]
S3_US_WEST = [
    {"region": "US West (Oregon) Region",
     "endpoint": "https://s3-us-west-2.amazonaws.com"},
    {"region": "US West (Northern California) Region",
     "endpoint": "https://s3-us-west-1.amazonaws.com"}]
S3_ASIA_PACIFIC = [
    {"region": "Asia Pacific (Singapore) Region",
     "endpoint": "https://s3-ap-southeast-1.amazonaws.com"},
    {"region": "Asia Pacific (Tokyo) Region",
     "endpoint": "https://s3-ap-northeast-1.amazonaws.com"}]
S3_US = S3_US_DEFAULT + S3_US_WEST
S3_EU_WEST = [
    {"region": "EU (Ireland) Region",
     "endpoint": "https://s3-eu-west-1.amazonaws.com"}]
S3_EU = S3_EU_WEST
S3_SOUTH_AMERICA_EAST = [
    {"region": "South America (Sao Paulo) Region",
     "endpoint": "s3-sa-east-1.amazonaws.com"}]
S3_SOUTH_AMERICA = S3_SOUTH_AMERICA_EAST
S3_ALL_REGIONS = S3_US + S3_ASIA_PACIFIC + S3_EU + S3_SOUTH_AMERICA
