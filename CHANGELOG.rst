4.1.0 (2016-09-26)
---------------------
- Drop support for Python 2.6, fixing a build failure due to attrs not being Python 2.6 compatible anymore.

4.0.1 (2016-07-18)
---------------------
- Throw HTTPTimeoutError only if it was caused by CancelledError (bugfix).

4.0.0 (2016-07-08)
---------------------
- Refactoring exceptions to distinguish between Connection errors and HTTP request/response errors.

3.2.1 (2016-06-16)
---------------------
- Fido is daemonization-safe with a solution similar to the one on crochet (reactor is not initialized at fido import time, see https://github.com/itamarst/crochet/issues/45). Forking is still discouraged.

3.2.0 (2016-05-20)
---------------------
- Fido is python 3 ready.
- Bytes are required for body now.
- User agent must be passed as any other header to fetch()

3.1.0 (2016-05-13)
---------------------
- Don't send content-type='application/json' by default anymore.

3.0.0 (2016-04-27)
---------------------
- Fido twisted client redesigned by the book (Twisted Network Programming Essentials).
- Fix CRITICAL :: twisted - Unhandled error in Deferred.
- Fix use of crochet library handling the reactor thread (@run_in_reactor and EventualResult).
- Drop concurrent.futures in favor of crochet EventualResult.
- Improved handling of timeout errors and exceptions in reactor thread.
- Increased test coverage and documentation.

2.1.4 (2016-04-18)
---------------------
- Don't unnecessarily constrain the version of twisted when not using python 2.6.

2.1.3 (2016-04-13)
---------------------
- Remove content-length when using FileBodyProducer

2.1.2 (2015-08-10)
---------------------
- Fix issue where errors from a request aren't getting raised.

2.1.1 (2015-08-07)
---------------------
- Fix duplicate Content-Length request headers when body is not empty. Twisted already takes care of this.

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
