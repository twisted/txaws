from zope.interface import implements

from twisted.internet.defer import succeed
from twisted.web.iweb import IBodyProducer

class StringBodyProducer(object):
    implements(IBodyProducer)

    def __init__(self, data):
        self.data = data
        self.length = len(data)
        self.written = None

    def startProducing(self, consumer):
        consumer.write(self.data)
        self.written = self.data
        return succeed(None)

    def pauseProducing(self):
        pass

    def stopProducing(self):
        pass
