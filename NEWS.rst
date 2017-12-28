Txaws 0.5.0 (2017-12-27)
========================

Features
--------

- txaws.s3.client.S3Client.get_bucket now accepts a ``prefix`` parameter for
  selecting a subset of S3 objects. (#78)
- txaws.ec2.client.EC2Client now has a ``get_console_output`` method binding
  the ``GetConsoleOutput`` API. (#82)


Txaws 0.4.0 (2017-07-04)
========================

Bugfixes
--------

- txaws now correctly signs requests with paths that require urlencoding. (#20)


Features
--------

- txaws now uses towncrier to produce news files. (#28)
- The Route53 client now recognizes all of the basic resource record types.
  (#50)
- txaws now supports reading the AWS_SHARED_CREDENTIALS_FILE and environment
  variable. (#52)
- txAWS now raises a CredentialsNotFoundError when it cannot locate
  credentials. Catching the previously-raised ValueError is now deprecated.
  (#53)
- txaws.credentials.AWSCredentials now supports loading different sets of
  credentials via AWS_PROFILE. (#54)


Misc
----

- #56, #57, #58, #62, #72
