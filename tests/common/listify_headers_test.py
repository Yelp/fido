import mock

from fido.common import listify_headers


def test_header_value_if_list_is_not_modified():
    header = {'foo': ['bla']}
    with mock.patch('fido.common.Headers') as mock_header:
        listify_headers(header)
    mock_header.assert_called_once_with(header)


def test_header_value_if_not_list_gets_changed_to_list():
    header = {'foo': 'bla'}
    new_header = {'foo': ['bla']}
    with mock.patch('fido.common.Headers') as mock_header:
        listify_headers(header)
    mock_header.assert_called_once_with(new_header)
