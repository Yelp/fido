# -*- coding: utf-8 -*-
import mock

import pytest
from twisted.internet.defer import Deferred

import fido
from fido.fido import _build_body_producer
from fido.fido import _set_deferred_timeout
from fido.fido import _twisted_web_client


TIMEOUT_TEST = 1.0
ERROR_MESSAGE = 'I failed :('


def test_set_deferred_timeout_none():
    mock_reactor = mock.Mock()
    mock_deferred = mock.Mock()
    _set_deferred_timeout(mock_reactor, mock_deferred, None)

    assert mock_reactor.callLater.called is False
    assert mock_deferred.addBoth.called is False


def test_set_deferred_timeout_finite_value():
    mock_reactor = mock.Mock()
    mock_deferred = mock.Mock()

    _set_deferred_timeout(mock_reactor, mock_deferred, TIMEOUT_TEST)

    mock_reactor.callLater.assert_called_once_with(
        TIMEOUT_TEST, mock_deferred.cancel
    )

    assert mock_deferred.addBoth.called is True


def test_headers_keep_content_length_if_no_body():
    headers = {'Content-Length': '0'}
    bodyProducer, headers = _build_body_producer(None, headers)
    assert bodyProducer is None
    assert 'Content-Length' in headers


@pytest.mark.parametrize(
    'header', ('content-length', 'Content-Length')
)
def test_headers_remove_content_length_if_body(header):
    headers = {header: '22'}
    body = b'{"some_json_data": 30}'

    bodyProducer, headers = _build_body_producer(body, headers)
    assert isinstance(bodyProducer, _twisted_web_client().FileBodyProducer)
    assert headers == {}


def test_headers_not_modified_in_place():
    headers = {'foo': 'bar', 'Content-Length': '22'}
    body = b'{"some_json_data": 30}'
    _, _ = _build_body_producer(body, headers)

    assert headers == {'foo': 'bar', 'Content-Length': '22'}


def test_get_agent_no_http_proxy():
    with mock.patch.dict('os.environ', clear=True):
        agent = fido.fido.get_agent(
            mock.Mock(spec=_twisted_web_client().Agent),
            connect_timeout=None)
    assert isinstance(agent, _twisted_web_client().Agent)


def test_get_agent_with_http_proxy():
    with mock.patch.dict('os.environ',
                         {'http_proxy': 'http://localhost:8000'}):
        agent = fido.fido.get_agent(
            mock.Mock(spec=_twisted_web_client().Agent),
            connect_timeout=None)
    assert isinstance(agent, _twisted_web_client().ProxyAgent)


def test_deferred_errback_chain():
    """
    Test exception thrown on the deferred correctly triggers the errback chain
    and it is thrown by EventualResult on result retrieval.
    """
    d = Deferred()
    mock_agent = mock.Mock()
    mock_agent.request.return_value = d

    # careful while patching get_agent cause it's being accessed
    # by the reactor thread
    with mock.patch('fido.fido.get_agent', return_value=mock_agent):
        eventual_result = fido.fido.fetch('http://some_url')

        # trigger an exception on the deferred
        d.errback(_twisted_web_client().ResponseFailed(ERROR_MESSAGE))

        with pytest.raises(_twisted_web_client().ResponseFailed) as e:
            eventual_result.wait(timeout=TIMEOUT_TEST)

        assert e.value.args == (ERROR_MESSAGE,)


def test_fetch_inner_exception_thrown_in_reactor_thread():
    """
    Test that an exception thrown in the reactor thread is trapped inside
    the EventualResult and thrown on result retrieval.
    """

    # careful while patching _build_body_producer cause it's being accessed
    # by the reactor thread
    with mock.patch('fido.fido.get_agent'):
        with mock.patch(
            'fido.fido._build_body_producer',
            side_effect=ValueError(ERROR_MESSAGE)
        ):

            # this should NOT raise! Exception is thrown in the reactor thread
            # and it is catched and saved inside EventualResult
            eventual_result = fido.fido.fetch('http://some_url')

            # exception should be thrown here, when waiting for the result
            with pytest.raises(ValueError) as e:
                eventual_result.wait(timeout=TIMEOUT_TEST)

            assert e.value.args == (ERROR_MESSAGE,)


def test_fetch_normally_throws_exception():
    """
    Testing an exception in the main thread of execution is normally thrown.
    """

    with mock.patch(
        'fido.fido.crochet.setup',
        side_effect=ValueError(ERROR_MESSAGE)
    ):
        with pytest.raises(ValueError) as e:
            fido.fido.fetch('http://some_url')

    assert e.value.args == (ERROR_MESSAGE,)
