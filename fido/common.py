import six
from twisted.web.http_headers import Headers
from yelp_bytes import to_bytes


def listify_headers(headers):
    """Twisted agent requires header values as lists"""

    for key, val in six.iteritems(headers):
        if not isinstance(val, list):
            headers[key] = [to_bytes(val)]
        else:
            headers[key] = [to_bytes(x) for x in val]
    return Headers(headers)
