# -*- coding: utf-8 -*-


class ConnectionError(Exception):
    """
    Base class for all errors due to connection problems (connection failing
    for any reason, including timeout reasons).
    """


class TCPConnectError(ConnectionError):
    """
    A connection error occurred for some reasons.
    A common reason is the connection took too long to establish.
    """


class HTTPTimeoutError(ConnectionError):
    """
    HTTP response was never received.
    A common reason is the server took too long to respond.
    """
