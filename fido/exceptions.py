# -*- coding: utf-8 -*-
import crochet
import zlib


class NetworkError(Exception):
    """
    Base class for all errors due to connection problems (connection failing
    for any reason, including timeout reasons).
    """


class TCPConnectionError(NetworkError):
    """
    A connection error occurred for some reasons.
    A common reason is the connection took too long to establish.
    """


class HTTPTimeoutError(NetworkError, crochet.TimeoutError):
    """
    HTTP response was never received.
    A common reason is the server took too long to respond.
    We're also inheriting from `crochet.TimeoutError` so we're backwards
    compatible with code that catches that exception (which is what we used
    to raise previously).
    """


class GzipDecompressionError(zlib.error):
    """
    Failed to decompress a gzip-enabled response.
    A server may return a response that is not compressed or has an
    unsupported format.
    """
