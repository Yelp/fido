# -*- coding: utf-8 -*-
from __future__ import absolute_import
import io
import json
import os

import crochet
import six
from six.moves.urllib_parse import urlparse
from twisted.internet.defer import CancelledError
from twisted.internet.defer import Deferred
from twisted.internet.endpoints import TCP4ClientEndpoint
from twisted.internet.error import ConnectError
from twisted.internet.protocol import Protocol
from yelp_bytes import to_bytes

from . import __about__
from .common import listify_headers
from fido.exceptions import TCPConnectionError
from fido.exceptions import HTTPTimeoutError


##############################################################################
# Twisted reactor is initialized at import time but this is problematic
# in the context of daemonization.
# Reactor initializes a couple of file descriptors (i.e. a pipe for eventpoll).
# If the fds are closed after the process daemonizes this could cause problems
# ('Bad File Descriptor' exceptions).
##############################################################################

def _import_reactor():
    from twisted.internet import reactor
    return reactor


def _twisted_web_client():
    from fido._client import _twisted_web_client
    return _twisted_web_client()


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
    bodyProducer = _twisted_web_client().FileBodyProducer(io.BytesIO(body))

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

        if (reason.check(_twisted_web_client().ResponseDone) or
                reason.check(_twisted_web_client().PotentialDataLoss)):
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
def fetch_inner(
    url,
    method,
    headers,
    body,
    timeout,
    connect_timeout,
    tcp_nodelay,
):
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
    reactor = _import_reactor()

    agent = get_agent(reactor, connect_timeout, tcp_nodelay)

    deferred = agent.request(
        method=method,
        uri=url,
        headers=listify_headers(twisted_headers),
        bodyProducer=bodyProducer,
    )

    def response_callback(response):
        """Fetch the body once we've received the headers"""
        finished = Deferred()
        response.deliverBody(HTTPBodyFetcher(response, finished))
        return finished

    deferred.addCallback(response_callback)

    def handle_timeout_errors(error):
        """
        This errback handles twisted timeout errors and wraps them as fido
        exceptions so that users don't need to import twisted APIs (reactor
        initialization issues) and dig into Twisted documentation and code.

        From the user's perspective and for sanity of usage is better to raise
        the friendlier fido.exception errors.
        """

        if error.check(_twisted_web_client().ResponseNeverReceived):
            if error.value.reasons[0].check(CancelledError):
                raise HTTPTimeoutError(
                    "Connection was closed by fido because the server took "
                    "more than timeout={timeout} seconds to "
                    "send the response".format(timeout=timeout)
                )

        elif error.check(ConnectError):
            raise TCPConnectionError(
                "Connection was closed by Twisted Agent because there was "
                "a problem establishing the connection or the "
                "connect_timeout={connect_timeout} was reached."
                .format(connect_timeout=connect_timeout)
            )
        return error

    deferred.addErrback(handle_timeout_errors)

    # sets timeout if it is not None
    _set_deferred_timeout(reactor, deferred, timeout)

    return deferred


def get_agent(reactor, connect_timeout=None, tcp_nodelay=False):
    """Return appropriate agent based on whether an http_proxy is used or not.

    :param connect_timeout: connection timeout in seconds
    :type connect_timeout: float
    :param tcp_nodelay: flag to enable tcp_nodelay for request
    :type tcp_nodelay: boolean
    :returns: :class:`twisted.web.client.ProxyAgent` when an http_proxy
        environment variable is present, :class:`twisted.web.client.Agent`
        otherwise.
    """

    # TODO: Would be nice to have https_proxy support too.
    http_proxy = os.environ.get('http_proxy')

    pool = None

    if tcp_nodelay:
        from fido._client import HTTPConnectionPoolOverride
        pool = HTTPConnectionPoolOverride(reactor=reactor, persistent=False)

    if http_proxy is None:
        return _twisted_web_client().Agent(
            reactor,
            connectTimeout=connect_timeout,
            pool=pool,
        )

    parse_result = urlparse(http_proxy)
    http_proxy_endpoint = TCP4ClientEndpoint(
        reactor,
        parse_result.hostname,
        parse_result.port or 80,
        timeout=connect_timeout)

    return _twisted_web_client().ProxyAgent(http_proxy_endpoint, pool=pool)


def fetch(
    url,
    method='GET',
    headers=None,
    body='',
    timeout=DEFAULT_TIMEOUT,
    connect_timeout=DEFAULT_CONNECT_TIMEOUT,
    tcp_nodelay=False,
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
    :param tcp_nodelay: flag to enable tcp_nodelay for request

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
    return fetch_inner(
        url,
        method,
        headers,
        body,
        timeout,
        connect_timeout,
        tcp_nodelay,
    )
