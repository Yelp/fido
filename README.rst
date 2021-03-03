Fido
********
.. image:: https://travis-ci.org/Yelp/fido.svg?branch=master
    :target: https://travis-ci.org/Yelp/fido

.. image:: https://coveralls.io/repos/Yelp/fido/badge.svg
  :target: https://coveralls.io/r/Yelp/fido

.. image:: https://img.shields.io/pypi/v/fido.svg
  :target: https://pypi.python.org/pypi/fido/
  :alt: PyPI version

.. image:: https://img.shields.io/pypi/pyversions/fido.svg
  :target: https://pypi.python.org/pypi/fido/
  :alt: Supported Python versions
  
Fido is now RETIRED, meaning that it will no longer be updated. Please consider using other libraries such as aiohttp.

Introduction
============

Fido is a simple, asynchronous HTTP client built on top of Crochet_ and Twisted_ with an implementation inspired by the book_ "Twisted Network Programming Essentials".  It is intended to be used in environments
where there is no event loop, and where you cannot afford to spin up lots of threads (otherwise you could just use a `ThreadPoolExecutor`_).

Here is an example of using Fido::

    future = fido.fetch('http://www.example.com')
    # Work happens in a background thread...
    response = future.wait(timeout=2)
    print(response.body)

Frequently Asked Questions
==========================

Do you support TLS?
-------------------

Yes, although this has not been vetted by security professionals.
One should use this functionality at their own risk.
In more detail: Fido uses the Twisted defaults, which delegate to
pyOpenSSL_ and `service_identity`_ for the actual TLS work.

Note that to get this you need to install the `tls` extra::

    $ pip install --upgrade fido[tls]

Is the API stable?
------------------

Probably not.  However, it is currently very simple, so it shouldn't be hard
to upgrade code if there's a non backwards-compatible change.

Do I need to initialize `Crochet`_?
-----------------------------------

No, `crochet.setup`_ is automatically invoked by `fido.fetch`.

How do I use an http_proxy?
---------------------------

Just set the http_proxy (all lowercase) environment variable to the URL of
the http proxy before starting your python process.

Example::

    $ export http_proxy="http://localhost:8000"
    $ python -c 'import fido; print(fido.fetch("http://www.example.com").wait().body)'



Installation
=============

Fido can be installed using `pip install`, like so::

    $ pip install --upgrade fido

If you want TLS capabilities::

    $ pip install --upgrade fido[tls]

License
========

Copyright (c) 2015, Yelp, Inc. All rights reserved.
Apache v2


.. _Crochet: https://github.com/itamarst/crochet
.. _crochet.setup: https://crochet.readthedocs.org/en/latest/api.html#setup
.. _Twisted: https://twistedmatrix.com/trac/
.. _concurrent.futures: http://pythonhosted.org/futures/
.. _ThreadPoolExecutor: http://pythonhosted.org/futures/#threadpoolexecutor-objects
.. _pyOpenSSL: https://github.com/pyca/pyopenssl
.. _service_identity: https://github.com/pyca/service_identity
.. _book: http://dl.acm.org/citation.cfm?id=1205685

