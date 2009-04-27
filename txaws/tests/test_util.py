from twisted.trial.unittest import TestCase

from txaws.util import *

class MiscellaneousTests(TestCase):

    def test_hmac_sha1(self):
        cases = [
            ('0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b'.decode('hex'),
             'Hi There', 'thcxhlUFcmTii8C2+zeMjvFGvgA='),
            ('Jefe', 'what do ya want for nothing?',
             '7/zfauXrL6LSdBbV8YTfnCWafHk='),
            ('aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'.decode('hex'),
             '\xdd' * 50, 'El1zQrmsEc2Ro5r0iqF7T2PxddM='),
            ]

        for key, data, expected in cases:
            self.assertEqual(hmac_sha1(key, data), expected)

    def test_iso8601time(self):
        self.assertEqual("2006-07-07T15:04:56Z", iso8601time((2006,7,7,15,4,56,
            0, 0, 0)))
