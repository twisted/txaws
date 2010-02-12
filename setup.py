from distutils.core import setup
from glob import glob
import os

from txaws import version


long_description = """
Twisted-based Asynchronous Libraries for Amazon Web Services and Eucalyptus
private clouds This project's goal is to have a complete Twisted API
representing the spectrum of Amazon's web services as well as support for
Eucalyptus clouds.
"""


def find_packages():
    """
    Compatibility wrapper.

    Taken from storm setup.py.
    """
    try:
        from setuptools import find_packages
        return find_packages()
    except ImportError:
        pass
    packages = []
    for directory, subdirectories, files in os.walk("txaws"):
        if '__init__.py' in files:
            packages.append(directory.replace(os.sep, '.'))
    return packages


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
        "Intended Audience :: by End-User Class :: Advanced End Users",
        "Intended Audience :: by End-User Class :: System Administrators",
        "Intended Audience :: by Industry or Sector :: Information Technology",
        "Programming Language :: Python",
        "Topic :: Database",
        "Topic :: Formats and Protocols :: Data Formats",
        "Topic :: Multimedia :: Graphics :: Presentation",
        "Topic :: Software Development :: Object Oriented",
        "Topic :: System :: Networking :: Monitoring",
        "Topic :: System :: Systems Administration",
        "License :: OSI Approved :: BSD License",
       ],
    )

