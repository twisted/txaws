from distutils.core import setup
from glob import glob
import os

from txaws import version

# If setuptools is present, use it to find_packages(), and also
# declare our dependency on epsilon.
extra_setup_args = {}
try:
    import setuptools
    from setuptools import find_packages
    extra_setup_args['install_requires'] = ['Epsilon']
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
    description="Async library for EC2 and Eucalyptus",
    author="txAWS Developers",
    author_email="txaws-discuss@lists.launchpad.net",
    url="https://launchpad.net/txaws",
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
    **extra_setup_args
    )

