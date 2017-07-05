import crochet

import fido.exceptions


def test_timeout_error_is_compatible_crochet():
    """Make sure the timeout exception we raise is compatible with old fido
    versions. We used to raise a `crochet.TimeoutError`.
    """
    timeout_exc = fido.exceptions.HTTPTimeoutError()
    assert isinstance(timeout_exc, crochet.TimeoutError)
