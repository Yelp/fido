# -*- coding: utf-8 -*-
import mock

from fido.common import encode_to_bytes
from fido.common import listify_headers


def test_list_value_not_listified():
    header = {'foo': ['bla']}
    new_header = {'foo': [b'bla']}
    with mock.patch('fido.common.Headers') as mock_header:
        listify_headers(header)
    mock_header.assert_called_once_with(new_header)


def test_header_value_listified():
    header = {'foo': 'bla'}
    new_header = {'foo': [b'bla']}
    with mock.patch('fido.common.Headers') as mock_header:
        listify_headers(header)
    mock_header.assert_called_once_with(new_header)


def test_encode_to_bytes():
    assert encode_to_bytes(u'繁') == b'\xe7\xb9\x81'


def test_encode_bytes_to_bytes():
    assert encode_to_bytes(b'skynet') == b'skynet'
