2.1.1 (2015-XX-XX)
---------------------
- Fix duplicate Content-Length request headers. Twisted already takes care of this.

2.1.0 (2015-08-06)
---------------------
- Add reason to fido.Response

2.0.1 (2015-08-04)
---------------------
- Don't schedule a timer cancelation when the timeout is None

2.0.0 (2015-07-29)
---------------------
- Default timeout in fido.fetch(..) has changed from 1s to None (wait indefinitely).
  This will change the behavior of existing code that doesn't pass in a timeout
  explicitly.

1.1.4 (2015-07-23)
---------------------
- Add support for connect_timeout
- Add CHANGELOG

1.1.3 (2015-07-14)
---------------------
- Issue #1 - Listify headers

1.1.2 (2015-05-11)
---------------------
- Fix Content-Length header to be a string

1.1.1 (2015-05-08)
----------------------
- Fix flaky unit tests

1.1.0 (2015-05-08)
----------------------
- Add http proxy support

1.0.1 (2015-03-12)
----------------------
- Fix unicode issues
