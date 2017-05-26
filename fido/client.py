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
    def _newConnection(self, key, endpoint):
        def quiescentCallback(protocol):
            self._putConnection(key, protocol)
        factory = HTTP11ClientFactoryOverride(quiescentCallback)
        return endpoint.connect(factory)
