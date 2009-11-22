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
    parser.add_option(
        "-o", "--object-name", dest="object_name", help="name of the object")
    parser.add_option(
        "-d", "--object-data", dest="object_data",
        help="content data of the object")
    parser.add_option(
        "--object-file", dest="object_filename",
        help=("the path to the file that will be saved as an object; if "
               "provided, the --object-name and --object-data options are "
               "not necessary"))
    parser.add_option(
        "-c", "--content-type", dest="content_type",
        help="content type of the object")
    options, args = parser.parse_args()
    if not (options.access_key and options.secret_key):
        parser.error(
            "both the access key ID and the secret key must be supplied")
    region = options.region
    if region and region.upper() not in ["US", "EU"]:
        parser.error("region must be one of 'US' or 'EU'")
    return (options, args)
