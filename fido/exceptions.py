# -*- coding: utf-8 -*-


class BaseTimeoutError(Exception):
    """
    Base class for all errors due to timeouts.
    """


class ConnectTimeoutError(BaseTimeoutError):
    """
    Connection took too long to establish
    """


class HTTPTimeoutError(BaseTimeoutError):
    """
    Server took too long to send the response.
    """
