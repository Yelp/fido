# -*- coding: utf-8 -*-
from __future__ import absolute_import
import io
import json
import os

import crochet
from twisted.internet import reactor
from twisted.internet.defer import Deferred
from twisted.internet.endpoints import TCP4ClientEndpoint
from twisted.internet.protocol import Protocol
import six
import twisted.web.client
from six.moves.urllib_parse import urlparse
from twisted.web.client import Agent, ProxyAgent
from twisted.web.client import FileBodyProducer

from . import __about__
from .common import listify_headers


DEFAULT_USER_AGENT = 'Fido/%s' % __about__.__version__
DEFAULT_CONTENT_TYPE = 'application/json'

# infinite timeouts are bad
DEFAULT_TIMEOUT = 30
DEFAULT_CONNECT_TIMEOUT = 30


def _url_to_utf8(url):
    """Makes sure the url is utf-8 encoded"""

    if isinstance(url, six.text_type):
        return url.encode('utf-8')
    return url


def _build_body_producer(body, headers):
    """
    Prepares the body and the headers for the twisted http request performed
    by the Twisted Agent.

    :returns: a Twisted FileBodyProducer object as required by Twisted Agent
    """

    if not body:
        return None, headers

    bodyProducer = FileBodyProducer(io.BytesIO(body))
    # content-length needs to be removed because it was computed based on
    # body but body is now being processed by twisted FileBodyProducer
    # causing content-length to lose meaning and break the client.
    # FileBodyProducer will take care of re-computing length and re-adding
    # a new content-length header later.
    headers = dict(
        (key, value)
        for (key, value) in six.iteritems(headers)
        if key.lower() != 'content-length'
    )

    return bodyProducer, headers


class Response(object):
    """An HTTP response.

    :ivar code: the integer response code.
    :ivar headers: a dictionary of response headers, mapping from string keys
        to lists of string values.
    :ivar body: the response body.
    :ivar reason: the http reason phrase.
    """

    def __init__(self, code, headers, body, reason):
        self.headers = dict(headers.getAllRawHeaders())
        self.code = code
        self.body = body
        self.reason = reason

    def json(self):
        """Helper function to load a JSON response body."""
        return json.loads(self.body)


class HTTPBodyFetcher(Protocol):

    def __init__(self, response, finished):
        self.buffer = io.BytesIO()
        self.response = response
        self.finished = finished

    def dataReceived(self, data):
        self.buffer.write(data)

    def connectionLost(self, reason):
        """
        :param reason:
            twisted.web.client.ResponseDone indicates that all bytes from the
                response have been successfully delivered
            twisted.web.client.PotentialDataLoss if it cannot be
                determined if the entire response body has been delivered.
                This only occurs when making requests to HTTP servers which do
                not set Content-Length or a Transfer-Encoding in the response
            twisted.web.client.ResponseFailed indicates that some bytes from
                the response were lost. The reasons attribute of the exception
                may provide more specific indications as to why.

        """

        if (reason.check(twisted.web.client.ResponseDone) or
                reason.check(twisted.web.http.PotentialDataLoss)):
            self.finished.callback(
                Response(
                    code=self.response.code,
                    headers=self.response.headers,
                    body=self.buffer.getvalue(),
                    reason=self.response.phrase,
                )
            )
        else:
            self.finished.errback(reason)


@crochet.run_in_reactor
def fetch_inner(url, method, headers, body, timeout, connect_timeout):
    """
    This function must be run in the reactor thread because it is calling
    twisted API which is not thread safe.
    See https://crochet.readthedocs.org/en/1.4.0/api.html#run-in-reactor-\
    asynchronous-results for additional information.

    The implementation of this function with regards to how to use the Twisted
    Agent is following the official book Twisted Network Programming Essentials

    :param connect_timeout: maximum time to set up the http connection before
        aborting. Note that after it is set up, `connect_timeout` loses value.
        If the server takes forever to send the response and if `timeout` is
        not provided, we could block forever.
    :param timeout: maximum time for the server to send a response back before
        we abort.

    :return: a crochet EventualResult wrapping a
        twisted.internet.defer.Deferred object
    """

    bodyProducer, headers = _build_body_producer(body, headers)

    deferred = get_agent(reactor, connect_timeout).request(
        method=method,
        uri=url,
        headers=listify_headers(headers),
        bodyProducer=bodyProducer)

    # Fetch the body once we've received the headers
    def response_callback(response):
        finished = Deferred()
        response.deliverBody(HTTPBodyFetcher(response, finished))
        return finished

    deferred.addCallback(response_callback)

    # erroback which handles various types of twisted timeout errors
    def handle_timeout_errors(error):
        if error.check(twisted.web.client.ResponseNeverReceived):
            if error.value.reasons[0].check(
                twisted.internet.defer.CancelledError
            ):
                raise crochet.TimeoutError(
                    "Connection was closed because the server took more than "
                    "`connect_timeout` seconds to send the response."
                )

        elif error.check(twisted.internet.error.TimeoutError):
            raise crochet.TimeoutError(
                "Connection was closed by Twisted Agent because the HTTP "
                "connection took to long to establish."
            )
        return error

    deferred.addErrback(handle_timeout_errors)

    # if the timeout is hit, set a timer to cancel the request
    timer = reactor.callLater(timeout, deferred.cancel)

    # if request is completed on time, cancel the timer
    def request_completed_on_time(response):
        if timer.active():
            timer.cancel()
        # pass the response through
        return response

    deferred.addBoth(request_completed_on_time)

    return deferred


def get_agent(reactor, connect_timeout=None):
    """Return appropriate agent based on whether an http_proxy is used or not.

    :param connect_timeout: connection timeout in seconds
    :type connect_timeout: float
    :returns: :class:`twisted.web.client.ProxyAgent` when an http_proxy
        environment variable is present, :class:`twisted.web.client.Agent`
        otherwise.
    """
    # TODO: Would be nice to have https_proxy support too.
    http_proxy = os.environ.get('http_proxy')
    if http_proxy is None:
        return Agent(reactor, connectTimeout=connect_timeout)

    parse_result = urlparse(http_proxy)
    http_proxy_endpoint = TCP4ClientEndpoint(
        reactor,
        parse_result.hostname,
        parse_result.port or 80,
        timeout=connect_timeout)

    return ProxyAgent(http_proxy_endpoint)


def fetch(
    url, method='GET', headers=None, body='', timeout=DEFAULT_TIMEOUT,
    connect_timeout=DEFAULT_CONNECT_TIMEOUT,
    content_type=DEFAULT_CONTENT_TYPE, user_agent=DEFAULT_USER_AGENT,
):
    """Make an HTTP request.

    :param url: the URL to fetch.
    :param timeout: maximum allowed request time, in seconds. Defaults to
        None which means to wait indefinitely.
    :param connect_timeout: maximum time allowed to establish a connection,
        in seconds.
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

    :returns: a crochet EventualResult object which behaves as a future,
        .wait() can be called on it to retrieve the fido.fido.Response object.
        .wait() throws any exception occurred while performing the request.
        Eventual additional failures information is stored in the crochet
        EventualResult object as stated in the official documentation

    """
    url = _url_to_utf8(url)

    # Make a copy to avoid mutating the original value
    headers = dict(headers or {})

    # Add basic header values if absent
    if 'User-Agent' not in headers:
        headers['User-Agent'] = [user_agent]
    if 'Content-Type' not in headers:
        headers['Content-Type'] = [content_type]

    # initializes twisted reactor in a different thread
    crochet.setup()
    return fetch_inner(url, method, headers, body, timeout, connect_timeout)
