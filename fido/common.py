import six
from twisted.web.http_headers import Headers


def listify_headers(headers):
    """Twisted agent requires header values as lists"""
    for key, val in six.iteritems(headers):
        if not isinstance(val, list):
            headers[key] = [val]
    return Headers(headers)
