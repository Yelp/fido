# -*- coding: utf-8 -*-
from __future__ import absolute_import
import io
import json
import os

import crochet
import six
import twisted.web.client
from six.moves.urllib_parse import urlparse
from twisted.internet import reactor
from twisted.internet.defer import Deferred
from twisted.internet.endpoints import TCP4ClientEndpoint
from twisted.internet.protocol import Protocol
from twisted.web.client import Agent
from twisted.web.client import ProxyAgent
from twisted.web.client import FileBodyProducer
from yelp_bytes import to_bytes

from . import __about__
from .common import listify_headers


DEFAULT_USER_AGENT = 'Fido/%s' % __about__.__version__

# Timeouts default to None which means block indefinitely according to the
# principle of least surprise. Famous examples following this pattern are:
# Requests, concurrent.futures, python socket stdlib
DEFAULT_TIMEOUT = None
DEFAULT_CONNECT_TIMEOUT = None


def _build_body_producer(body, headers):
    """
    Prepares the body and the headers for the twisted http request performed
    by the Twisted Agent.

    :param body: request body, MUST be of type bytes.

    :returns: a Twisted FileBodyProducer object as required by Twisted Agent
    """

    if not body:
        return None, headers

    # body must be of bytes type.
    bodyProducer = FileBodyProducer(io.BytesIO(body))

    # content-length needs to be removed because it was computed based on
    # body but body is now being processed by twisted FileBodyProducer
    # causing content-length to lose meaning and break the client.
    # FileBodyProducer will take care of re-computing length and re-adding
    # a new content-length header later.
    twisted_headers = dict(
        (key, value)
        for (key, value) in six.iteritems(headers)
        if key.lower() != 'content-length'
    )

    return bodyProducer, twisted_headers


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
        return json.loads(self.body.decode('utf-8'))


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

            For more info see https://twistedmatrix.com/documents/9.0.0/api/\
                twisted.web.client.Response.html
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


def _set_deferred_timeout(reactor, deferred, timeout):
    """
    NOTE: Make sure to call this only from the reactor thread as it is
    accessing twisted API.

    Sets a maximum timeout on the deferred object. The deferred will be
    cancelled after 'timeout' seconds. This timeout represents the maximum
    allowed time for Fido to wait for the server response after the connection
    has been established by the Twisted Agent.
    """

    if timeout is None:
        return

    # set a timer to cancel the deferred request when/if the timeout is hit
    cancel_deferred_timer = reactor.callLater(timeout, deferred.cancel)

    # if request is completed on time, cancel the timer
    def request_completed_on_time(response):
        if cancel_deferred_timer.active():
            cancel_deferred_timer.cancel()
        return response

    deferred.addBoth(request_completed_on_time)


@crochet.run_in_reactor
def fetch_inner(url, method, headers, body, timeout, connect_timeout):
    """
    This function must be run in the reactor thread because it is calling
    twisted API which is not thread safe.
    See https://crochet.readthedocs.org/en/1.4.0/api.html#run-in-reactor-\
    asynchronous-results for additional information.

    The implementation of this function with regards to how to use the Twisted
    Agent is following the official book Twisted Network Programming Essentials
    chapter 'Web Clients', paragraph 'Agent', page 55 - 2nd Edition.

    :param connect_timeout: maximum time to set up the http connection before
        aborting. Note that after it is set up, `connect_timeout` loses value.
        If the server takes forever to send the response and if `timeout` is
        not provided, we could block forever.
    :param timeout: maximum time for the server to send a response back before
        we abort.

    :return: a crochet EventualResult wrapping a
        twisted.internet.defer.Deferred object
    """

    bodyProducer, twisted_headers = _build_body_producer(body, headers)

    deferred = get_agent(reactor, connect_timeout).request(
        method=method,
        uri=url,
        headers=listify_headers(twisted_headers),
        bodyProducer=bodyProducer
    )

    def response_callback(response):
        """Fetch the body once we've received the headers"""
        finished = Deferred()
        response.deliverBody(HTTPBodyFetcher(response, finished))
        return finished

    deferred.addCallback(response_callback)

    def handle_timeout_errors(error):
        """
        This errback handles different types of twisted timeout errors. We
        could let these errors bubble up but the user would have to deal with
        twisted errors without knowing what caused them. From the user's
        perspective and for sanity of usage is better to raise the friendlier
        crochet.TimeoutError with an explanation of what happened.
        """

        if error.check(twisted.web.client.ResponseNeverReceived):
            if error.value.reasons[0].check(
                twisted.internet.defer.CancelledError
            ):
                raise crochet.TimeoutError(
                    "Connection was closed by fido because the server took "
                    "more than timeout={timeout} seconds to "
                    "send the response".format(timeout=timeout)
                )

        elif error.check(twisted.internet.error.TimeoutError):
            raise crochet.TimeoutError(
                "Connection was closed by Twisted Agent because the HTTP "
                "connection took more than connect_timeout={connect_timeout} "
                "seconds to establish.".format(connect_timeout=connect_timeout)
            )
        return error

    deferred.addErrback(handle_timeout_errors)

    # sets timeout if it is not None
    _set_deferred_timeout(reactor, deferred, timeout)

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
    url,
    method='GET',
    headers=None,
    body='',
    timeout=DEFAULT_TIMEOUT,
    connect_timeout=DEFAULT_CONNECT_TIMEOUT,
):
    """
    Make an HTTP request.

    :param url: the URL to fetch.
    :param method: the HTTP method.
    :param headers: a dictionary mapping from string keys to lists of string
        values.  For example::

            {
                'X-Foo': ['Bar'],
                'X-Baz': ['Quux'],
            }
    :param body: the request body (must be of bytes type).
    :param timeout: maximum allowed request time in seconds.
    :param connect_timeout: maximum time allowed to establish a connection
        in seconds.

    :returns: a crochet EventualResult object which behaves as a future,
        .wait() can be called on it to retrieve the fido.fido.Response object.
        .wait() throws any exception occurred while performing the request.
        Eventual additional failures information is stored in the crochet
        EventualResult object as stated in the official documentation

    """

    # Twisted requires the method, url, headers to be bytes
    url = to_bytes(url)
    method = to_bytes(method)

    # Make a copy to avoid mutating the original value
    headers = dict(headers or {})

    if not any(header.lower() == 'user-agent' for header in headers):
        headers['User-Agent'] = [DEFAULT_USER_AGENT]

    # initializes twisted reactor in a different thread
    crochet.setup()
    return fetch_inner(url, method, headers, body, timeout, connect_timeout)
