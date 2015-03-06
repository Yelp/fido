from fido import fetch


def test_fido_request_throws_no_timeout_when_header_value_not_list():
    fetch('http://www.yelp.com', headers={'Accept-Charset': 'utf-8',
                                          'Accept-Language': ['en-US']
                                          }).result(timeout=5)
