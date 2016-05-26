# -*- coding: utf-8 -*-
import mock

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
