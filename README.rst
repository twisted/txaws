txAWS
=====

.. image:: http://img.shields.io/pypi/v/txaws.svg
   :target: https://pypi.python.org/pypi/txaws
   :alt: PyPI Package

.. image:: https://travis-ci.org/twisted/txaws.svg
   :target: https://travis-ci.org/twisted/txaws
   :alt: CI status

.. image:: https://codecov.io/github/twisted/txaws/coverage.svg
   :target: https://codecov.io/github/twisted/txaws
   :alt: Coverage

What is this?
-------------

txAWS is a Twisted-based client library for interacting with Amazon Web Services.

Installing
----------

To install the latest version of txAWS using pip::

  $ pip install txaws

For additional development dependencies, install the ``dev`` extra::

  $ pip install txaws[dev]


Things present here
-------------------

* The txaws python package.

* bin/aws-status, a GUI status program for aws resources.

Testing
-------

txAWS includes a test suite which can be run by ``trial``::

  $ trial txaws

The test suite includes many unit tests which should run and pass on all supported platforms.
It also includes integration tests which require AWS credentials to be set in the environment.

  * ``TXAWS_INTEGRATION_AWS_ACCESS_KEY_ID`` set to an access key id
  * ``TXAWS_INTEGRATION_AWS_SECRET_ACCESS_KEY`` set to a secret access key

With these set in the environment, the test suite will automatically interact with AWS.
This includes creation and deletion of resources which will incur (minor) costs on AWS.
Attempts are made to clean up these resources but there is no guarantee this will happen.
After running the test suite, verify everything has been cleaned up to avoid additional costs.
``test-tools/aws-cleanup``\ , which will delete **all** AWS resources it finds, is provided to assist with cleanup.

License
-------

txAWS is open source software, MIT License.
See the LICENSE file for more details.
