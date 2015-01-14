import BaseHTTPServer
import json
import logging
import mock
import SocketServer
import threading
import time

import concurrent.futures
import pytest
import twisted.internet.error
import twisted.internet.defer

import sprocket


@pytest.yield_fixture(scope="module")
def server_url():
    """Spin up a localhost web server for testing."""

    # Surpress 'No handlers could be found for logger "twisted"' messages
    logging.basicConfig()
    logging.getLogger('twisted').setLevel(logging.CRITICAL)

    class MyHandler(BaseHTTPServer.BaseHTTPRequestHandler):
        def echo(self):
            if self.path == '/slow':
                time.sleep(1)
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            content_length = int(self.headers.get('Content-Length', 0))
            self.wfile.write(json.dumps({
                'headers': dict(self.headers),
                'method': self.command,
                'body': self.rfile.read(content_length)
            }))

        def do_GET(self):
            self.echo()

        def do_POST(self):
            self.echo()

    class MultiThreadedHTTPServer(SocketServer.ThreadingMixIn,
                                  BaseHTTPServer.HTTPServer):
        request_queue_size = 1000

    httpd = MultiThreadedHTTPServer(('localhost', 0), MyHandler)
    httpd_thread = threading.Thread(target=httpd.serve_forever)
    httpd_thread.start()
    yield 'http://%s:%d/' % (httpd.server_address[0], httpd.server_address[1])
    httpd.server_close()
    httpd_thread.join()


def test_fetch_basic(server_url):
    response = sprocket.fetch(server_url).result()
    assert 'Content-Type' in response.headers
    assert response.code == 200
    assert response.json()['method'] == 'GET'


def test_fetch_timeout(server_url):
    with pytest.raises(twisted.internet.defer.CancelledError):
        sprocket.fetch(server_url + 'slow', timeout=0.5).result()


def test_fetch_stress(server_url):
    futures = [sprocket.fetch(server_url, timeout=8) for _ in xrange(1000)]
    for future in concurrent.futures.as_completed(futures):
        future.result()


def test_fetch_method(server_url):
    expected_method = 'POST'
    future = sprocket.fetch(server_url, method=expected_method)
    actual_method = future.result().json()['method']
    assert expected_method == actual_method


def test_fetch_headers(server_url):
    headers = {'foo': ['bar']}
    future = sprocket.fetch(server_url, headers=headers)
    actual_headers = future.result().json()['headers']
    assert actual_headers.get('foo') == 'bar'


def test_fetch_content_type(server_url):
    expected_content_type = 'text/html'
    future = sprocket.fetch(server_url, content_type=expected_content_type)
    actual_content_type = future.result().json()['headers'].get('content-type')
    assert expected_content_type == actual_content_type


def test_fetch_user_agent(server_url):
    expected_user_agent = 'skynet'
    future = sprocket.fetch(server_url, user_agent=expected_user_agent)
    actual_user_agent = future.result().json()['headers'].get('user-agent')
    assert expected_user_agent == actual_user_agent


def test_fetch_body(server_url):
    expected_body = 'corpus'
    future = sprocket.fetch(server_url, body=expected_body)
    actual_body = future.result().json()['body']
    assert expected_body == actual_body


def test_future_callback(server_url):
    condition = threading.Condition()
    done_callback = mock.Mock()

    with condition:
        future = sprocket.fetch(server_url)
        future.add_done_callback(done_callback)
        condition.wait(1)
        done_callback.assert_called_once_with(future)


def test_future_cancel(server_url):
    # This is usually a no-op because we cannot cancel requests once they are
    # being processed, which happens almost instantaneously.
    future = sprocket.fetch(server_url)
    future.cancel()


def test_future_done(server_url):
    future = sprocket.fetch(server_url)
    future.result()
    assert future.done()


def test_future_timeout(server_url):
    with pytest.raises(concurrent.futures.TimeoutError):
        sprocket.fetch(server_url + 'slow').result(timeout=0.5)


def test_future_connection_refused():
    with pytest.raises(twisted.internet.error.ConnectionRefusedError):
        sprocket.fetch('http://localhost:0').result()


def test_future_exception(server_url):
    future = sprocket.fetch(server_url + 'slow', timeout=0.5)
    assert future.exception() is not None


def test_future_wait(server_url):
    futures = [sprocket.fetch(server_url) for _ in xrange(10)]
    done, not_done = concurrent.futures.wait(futures)

    assert len(done) == 10
    assert len(not_done) == 0
    for future in done:
        assert future.done()


def test_future_as_completed(server_url):
    futures = [sprocket.fetch(server_url) for _ in xrange(10)]
    for future in concurrent.futures.as_completed(futures):
        assert future.done()
