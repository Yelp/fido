"""
NOTE: Make sure to only import this module from the reactor thread as
      the class definitions call the Twisted API which is not thread safe.
"""


def _twisted_web_client():
    from twisted.web import client
    return client


class HTTP11ClientProtocolOverride(_twisted_web_client().HTTP11ClientProtocol):
    def connectionMade(self):
        self.transport.setTcpNoDelay(True)


class HTTP11ClientFactoryOverride(_twisted_web_client()._HTTP11ClientFactory):
    def buildProtocol(self, addr):
        return HTTP11ClientProtocolOverride(self._quiescentCallback)


class HTTPConnectionPoolOverride(_twisted_web_client().HTTPConnectionPool):
    _factory = HTTP11ClientFactoryOverride
