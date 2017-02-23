from distutils.core import setup
from glob import glob
import os

from txaws import version

# If setuptools is present, use it to find_packages(), and also
# declare our dependency on python-dateutil.
extra_setup_args = {}
try:
    from setuptools import find_packages
    extra_setup_args['install_requires'] = [
        'attrs', 'python-dateutil', 'twisted[tls]>=15.5.0,!=17.1.0', 'venusian', 'lxml',
        'incremental', 'pyrsistent', 'constantly',
    ]
except ImportError:
    def find_packages():
        """
        Compatibility wrapper.

        Taken from storm setup.py.
        """
        packages = []
        for directory, subdirectories, files in os.walk("txaws"):
            if '__init__.py' in files:
                packages.append(directory.replace(os.sep, '.'))
        return packages

long_description = """
Twisted-based Asynchronous Libraries for Amazon Web Services and Eucalyptus
private clouds This project's goal is to have a complete Twisted API
representing the spectrum of Amazon's web services as well as support for
Eucalyptus clouds.
"""


setup(
    name="txAWS",
    version=version.txaws,
    description="Async library for EC2, OpenStack, and Eucalyptus",
    author="txAWS Developers",
    url="https://github.com/twisted/txaws",
    license="MIT",
    packages=find_packages(),
    scripts=glob("./bin/*"),
    long_description=long_description,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "Intended Audience :: Information Technology",
        "Programming Language :: Python",
        "Topic :: Database",
        "Topic :: Internet :: WWW/HTTP",
        "License :: OSI Approved :: MIT License",
       ],
    include_package_data=True,
    zip_safe=False,
    extras_require={
        "dev": ["treq", "zope.datetime", "boto3"],
    },
    **extra_setup_args
    )
