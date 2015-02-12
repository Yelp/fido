from cStringIO import StringIO
import json

import concurrent.futures
import crochet
import twisted.web.client
from twisted.internet import reactor
from twisted.internet.defer import Deferred
from twisted.internet.protocol import Protocol
from twisted.web.client import Agent
from twisted.web.client import FileBodyProducer
from twisted.web.http_headers import Headers

import __about__


DEFAULT_USER_AGENT = 'Fido/%s' % __about__.__version__

DEFAULT_CONTENT_TYPE = 'application/json'

DEFAULT_TIMEOUT = 1.0


class Response(object):
    """An HTTP response.

    :ivar code: the integer response code.
    :ivar headers: a dictionary of response headers, mapping from string keys
        to lists of string values.
    :ivar body: the response body.
    """

    def __init__(self, code, headers, body):
        self.headers = dict(headers.getAllRawHeaders())
        self.code = code
        self.body = body

    def json(self):
        """Helper function to load a JSON response body."""
        return json.loads(self.body)


class HTTPBodyFetcher(Protocol):

    def __init__(self, response, finished):
        self.buffer = StringIO()
        self.response = response
        self.finished = finished

    def dataReceived(self, data):
        self.buffer.write(data)

    def connectionLost(self, reason):
        if (reason.check(twisted.web.client.ResponseDone) or
                reason.check(twisted.web.http.PotentialDataLoss)):
            self.finished.callback(
                Response(
                    code=self.response.code,
                    headers=self.response.headers,
                    body=self.buffer.getvalue(),
                )
            )
        else:
            self.finished.errback(reason)


@crochet.run_in_reactor
def fetch_inner(url, method, headers, body, future, timeout):
    """This runs inside a separate thread and orchestrates the async IO
    work.
    """

    finished = Deferred()

    # Set an exception on the future in case of error
    def finished_errorback(error):
        try:
            error.raiseException()
        except BaseException as e:
            future.set_exception(e)
    finished.addErrback(finished_errorback)

    # Set the result on the future in case of success
    finished.addCallback(future.set_result)

    bodyProducer = None
    if body:
        bodyProducer = FileBodyProducer(StringIO(body))
    deferred = Agent(reactor).request(
        method=method,
        uri=url,
        headers=Headers(headers),
        bodyProducer=bodyProducer)

    # Fetch the body once we've received the headers
    def response_callback(response):
        response.deliverBody(HTTPBodyFetcher(response, finished))
    deferred.addCallback(response_callback)
    deferred.addErrback(finished.errback)

    # Cancel the request if we hit the timeout
    def cancel_timer(response):
        if timer.active():
            timer.cancel()
        return response
    timer = reactor.callLater(timeout, deferred.cancel)
    finished.addBoth(cancel_timer)

    return finished


def fetch(url, timeout=DEFAULT_TIMEOUT, method='GET',
          content_type=DEFAULT_CONTENT_TYPE, user_agent=DEFAULT_USER_AGENT,
          headers={}, body=''):
    """Make an HTTP request.

    :param url: the URL to fetch.
    :param timeout: maximum allowed request time, in seconds.
    :param method: the HTTP method.
    :param headers: a dictionary mapping from string keys to lists of string
        values.  For example::

            {
                'X-Foo': ['Bar'],
                'X-Baz': ['Quux'],
            }

    :param content_type: the content type.
    :param user_agent: the user agent.
    :param body: the body of the request.

    :returns: a :py:class:`concurrent.futures.Future` that returns a
        :py:class:`Response` if the request is successful.
    """

    # Make a copy to avoid mutating the original value
    headers = dict(headers)

    # Add basic header values if absent
    if 'User-Agent' not in headers:
        headers['User-Agent'] = [user_agent]
    if 'Content-Type' not in headers:
        headers['Content-Type'] = [content_type]
    if 'Content-Length' not in headers and body:
        headers['Content-Length'] = [len(body)]

    crochet.setup()
    future = concurrent.futures.Future()
    if future.set_running_or_notify_cancel():
        fetch_inner(url, method, headers, body, future, timeout)
    return future
