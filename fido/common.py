# -*- coding: utf-8 -*-
import six
from twisted.web.http_headers import Headers
from yelp_bytes import to_bytes


def listify_headers(headers):
    """Twisted agent requires header values as lists"""
    byte_headers = {}
    for key, val in six.iteritems(headers):
        byte_key = to_bytes(key)
        if not isinstance(val, list):
            byte_headers[byte_key] = [to_bytes(val)]
        else:
            byte_headers[byte_key] = [to_bytes(x) for x in val]
    return Headers(byte_headers)
