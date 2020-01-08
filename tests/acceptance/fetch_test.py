# -*- coding: utf-8 -*-
import logging
import time

import zlib
from multiprocessing import Process

import crochet
import pytest
from six.moves import BaseHTTPServer
from six.moves import socketserver as SocketServer
from yelp_bytes import to_bytes

import fido
from fido.fido import DEFAULT_USER_AGENT
from fido.fido import GZIP_WINDOW_SIZE
from fido.exceptions import TCPConnectionError
from fido.exceptions import HTTPTimeoutError
from fido.exceptions import GzipDecompressionError


SERVER_OVERHEAD_TIME = 2.0
TIMEOUT_TEST = 1.0

ECHO_URL = '/echo'
GZIP_URL = '/gzip'


def _compress_gzip(buffer):
    compress_gzip = zlib.compressobj(
        zlib.Z_DEFAULT_COMPRESSION,
        zlib.DEFLATED,
        GZIP_WINDOW_SIZE,
    )
    return compress_gzip.compress(buffer) + compress_gzip.flush()


# Verifies that setting TCP_NODELAY does not affect
# the output of fido
@pytest.fixture(scope="module", params=[False, True])
def tcp_nodelay(request):
    return request.param


@pytest.yield_fixture(scope="module")
def server_url():
    """Spin up a localhost web server for testing."""

    # Surpress 'No handlers could be found for logger "twisted"' messages
    logging.basicConfig()
    logging.getLogger('twisted').setLevel(logging.CRITICAL)

    class TestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
        def echo(self):
            if 'slow' in self.path:
                time.sleep(SERVER_OVERHEAD_TIME)

            self.send_response(200)

            for k, v in self.headers.items():
                self.send_header(k, v)
            self.end_headers()

            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                self.wfile.write(self.rfile.read(content_length))

        def gzip(self):
            accept_encoding_headers = []
            for k, v in self.headers.items():
                if k.lower() == 'accept-encoding':
                    accept_encoding_headers.append(v)

            if 'gzip' not in accept_encoding_headers:
                self.send_response(500)
                self.end_headers()
                return

            self.send_response(200)
            self.send_header('Content-Encoding', 'gzip')
            self.end_headers()
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                self.wfile.write(_compress_gzip(
                    self.rfile.read(content_length)))

        def content_length(self):
            """Send back the content-length number as the response."""
            self.send_response(200)

            response = to_bytes(self.headers.get('Content-Length'))
            content_length = len(response)
            self.send_header('Content-Length', content_length)
            self.end_headers()

            self.wfile.write(response)

        def do_GET(self):
            if ECHO_URL in self.path:
                self.echo()
            elif GZIP_URL in self.path:
                self.gzip()

        def do_POST(self):
            if 'content_length' in self.path:
                self.content_length()
            elif ECHO_URL in self.path:
                self.echo()

    class MultiThreadedHTTPServer(
        SocketServer.ThreadingMixIn,
        BaseHTTPServer.HTTPServer
    ):
        request_queue_size = 1000

    httpd = MultiThreadedHTTPServer(('localhost', 0), TestHandler)
    web_service_process = Process(target=httpd.serve_forever)
    try:
        web_service_process.start()
        server_address = 'http://{host}:{port}'.format(
            host=httpd.server_address[0],
            port=httpd.server_address[1],
        )
        yield server_address
    finally:
        web_service_process.terminate()


def test_fetch_basic(server_url):
    response = fido.fetch(server_url + ECHO_URL).wait()
    assert response.headers.get(b'User-Agent') == \
        [to_bytes(DEFAULT_USER_AGENT)]
    assert response.reason == b'OK'
    assert response.code == 200


def test_eventual_result_timeout(server_url):
    """
    Testing timeout on result retrieval
    """

    # fetch without setting timeouts -> we could potentially wait forever
    eventual_result = fido.fetch(server_url + ECHO_URL + '/slow')

    # make sure no timeout error is thrown here but only on result retrieval
    assert eventual_result.original_failure() is None

    with pytest.raises(crochet.TimeoutError):
        eventual_result.wait(timeout=TIMEOUT_TEST)

    assert eventual_result.original_failure() is None


def test_agent_timeout(server_url, tcp_nodelay):
    """
    Testing that we don't wait forever on the server sending back a response
    """

    eventual_result = fido.fetch(
        server_url + ECHO_URL + '/slow',
        timeout=TIMEOUT_TEST,
        tcp_nodelay=tcp_nodelay,
    )

    # wait for fido to estinguish the timeout and abort before test-assertions
    time.sleep(2 * TIMEOUT_TEST)

    # timeout errors were thrown and handled in the reactor thread.
    # EventualResult stores them and re-raises on result retrieval
    assert eventual_result.original_failure() is not None

    with pytest.raises(HTTPTimeoutError) as e:
        eventual_result.wait()

    assert (
        "Connection was closed by fido because the server took "
        "more than timeout={timeout} seconds to "
        "send the response".format(timeout=TIMEOUT_TEST)
        in str(e)
    )


def test_agent_connect_timeout(tcp_nodelay):
    """
    Testing that we don't wait more than connect_timeout to establish a http
    connection
    """

    # google drops TCP SYN packets
    eventual_result = fido.fetch(
        "http://www.google.com:81",
        connect_timeout=TIMEOUT_TEST,
        tcp_nodelay=tcp_nodelay,
    )
    # wait enough for the connection to be dropped by Twisted Agent
    time.sleep(3 * TIMEOUT_TEST)

    # timeout errors were thrown and handled in the reactor thread.
    # EventualResult stores them and re-raises on result retrieval
    assert eventual_result.original_failure() is not None

    with pytest.raises(TCPConnectionError) as e:
        eventual_result.wait()

    assert (
        "Connection was closed by Twisted Agent because there was "
        "a problem establishing the connection or the "
        "connect_timeout={connect_timeout} was reached."
        .format(connect_timeout=TIMEOUT_TEST)
        in str(e)
    )


def test_fetch_headers(server_url, tcp_nodelay):
    headers = {'foo': ['bar']}
    eventual_result = fido.fetch(server_url + ECHO_URL,
                                 headers=headers,
                                 tcp_nodelay=tcp_nodelay)
    actual_headers = eventual_result.wait().headers
    assert actual_headers.get(b'Foo') == [b'bar']


def test_json_body(server_url, tcp_nodelay):
    body = b'{"some_json_data": 30}'
    eventual_result = fido.fetch(
        server_url + ECHO_URL,
        method='POST',
        body=body,
        tcp_nodelay=tcp_nodelay,
    )
    assert eventual_result.wait().json()['some_json_data'] == 30


def test_content_length_readded_by_twisted(server_url, tcp_nodelay):
    headers = {'Content-Length': '250'}
    body = b'{"some_json_data": 30}'
    eventual_result = fido.fetch(
        server_url + '/content_length',
        method='POST',
        headers=headers,
        body=body,
        tcp_nodelay=tcp_nodelay,
    )
    content_length = int(eventual_result.wait().body)
    assert content_length == 22


def test_fetch_content_type(server_url, tcp_nodelay):
    expected_content_type = b'text/html'
    eventual_result = fido.fetch(
        server_url + ECHO_URL,
        headers={'Content-Type': expected_content_type},
        tcp_nodelay=tcp_nodelay,
    )
    actual_content_type = eventual_result.wait().headers.\
        get(b'Content-Type')
    assert [expected_content_type] == actual_content_type


@pytest.mark.parametrize(
    'header_name', ('User-Agent', 'user-agent')
)
def test_fetch_user_agent(server_url, header_name, tcp_nodelay):
    expected_user_agent = [b'skynet']
    headers = {header_name: expected_user_agent}
    eventual_result = fido.fetch(
        server_url + ECHO_URL,
        headers=headers,
        tcp_nodelay=tcp_nodelay,
    )
    actual_user_agent = eventual_result.wait().headers.get(b'User-Agent')
    assert expected_user_agent == actual_user_agent


def test_fetch_body(server_url, tcp_nodelay):
    expected_body = b'corpus'
    eventual_result = fido.fetch(
        server_url + ECHO_URL,
        body=expected_body,
        tcp_nodelay=tcp_nodelay,
    )
    actual_body = eventual_result.wait().body
    assert expected_body == actual_body


def test_fido_request_no_timeout_when_header_value_not_list(tcp_nodelay):
    fido.fetch(
        'http://www.yelp.com',
        headers={
            'Accept-Charset': 'utf-8',
            'Accept-Language': ['en-US']
        },
        tcp_nodelay=tcp_nodelay,
    ).wait(timeout=5)


def test_fido_request_decompress_gzip(server_url):
    expected_body = b'hello world'

    # Ensure invalid gzipped responses raise a
    # GzipDecompressionError exception.
    with pytest.raises(GzipDecompressionError):
        # Here we trick the client into decompressing the text
        # response by echoing a gzip content-encoding response
        # header. The client should then fail to decompress the
        # text response.
        response = fido.fetch(
            server_url + ECHO_URL,
            headers={'Content-Encoding': 'gzip'},
            body=expected_body,
            decompress_gzip=True,
        ).wait()

    # Ensure valid gzipped responses are decompressed
    # when gzip_enabled is True.
    response = fido.fetch(
        server_url + GZIP_URL,
        # Ensure that fido successfully appends gzip to accept-encoding.
        headers={
            'Content-Encoding': 'gzip',
            'Accept-Encoding': 'deflate, br, identity'
        },
        body=expected_body,
        decompress_gzip=True,
    ).wait()
    actual_body = response.body
    assert response.code == 200
    assert expected_body == actual_body


def test_fido_request_gzip_disabled(server_url):
    expected_body = b'hello world'

    # Ensure that gzipped responses with decompress_gzip set
    # to false remain compressed.
    response = fido.fetch(
        server_url + GZIP_URL,
        body=expected_body,
        headers={'Accept-Encoding': 'gzip'},
        decompress_gzip=False,
    ).wait()
    actual_body = response.body
    assert response.code == 200
    assert _compress_gzip(expected_body) == actual_body
