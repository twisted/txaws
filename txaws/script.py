from optparse import OptionParser

from txaws import meta
from txaws import version


# XXX Once we start adding script that require conflicting options, we'll need
# multiple parsers and option dispatching...
def parse_options(usage):
    parser = OptionParser(usage, version="%s %s" % (
        meta.display_name, version.txaws))
    parser.add_option(
        "-a", "--access-key", dest="access_key", help="access key ID")
    parser.add_option(
        "-s", "--secret-key", dest="secret_key", help="access secret key")
    parser.add_option(
        "-r", "--region", dest="region", help="US or EU (valid for AWS only)")
    parser.add_option(
        "-U", "--url", dest="url", help="service URL/endpoint")
    parser.add_option(
        "-b", "--bucket", dest="bucket", help="name of the bucket")
    options, args = parser.parse_args()
    #if len(args) != 1:
    #    parser.error("incorrect number of arguments")
    # XXX check for creds defined in env
    if not (options.access_key and options.secret_key):
        parser.error(
            "both the access key ID and the secret key must be supplied")
    region = options.region.upper()
    if region and region not in ["US", "EU"]:
        parser.error("region must be one of 'US' or 'EU'")
    return (options, args)
