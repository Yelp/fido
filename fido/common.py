import six
from twisted.web.http_headers import Headers


def encode_to_bytes(value):
    """Twisted requires the method, url, headers to be utf-8 encoded"""

    if isinstance(value, six.text_type):
        return value.encode('utf-8')
    return value


def listify_headers(headers):
    """Twisted agent requires header values as lists"""

    for key, val in six.iteritems(headers):
        if not isinstance(val, list):
            headers[key] = [encode_to_bytes(val)]
        else:
            headers[key] = [encode_to_bytes(val[0])]
    return Headers(headers)
