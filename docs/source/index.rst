.. fido documentation master file, created by
   sphinx-quickstart on Fri May 13 14:16:02 2011.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Fido
********

Introduction
============

Fido is a simple, asynchronous HTTP client built on top of Crochet_,
Twisted_ and `concurrent.futures`_.  It is intended to be used in environments
where there is no event loop, and where you cannot afford to spin up lots of
threads (otherwise you could just use a `ThreadPoolExecutor`_).

Here is an example of using Fido::

    future = fido.fetch('http://www.example.com')
    # Work happens in a background thread...
    response = future.wait(timeout=2)
    print response.body

Frequently Asked Questions
==========================

Do you support SSL?
-------------------

Yes, but I don't know whether it's secure;  we should talk before you depend on
this functionality. In more detail: Fido uses the Twisted defaults,
which delegate to pyOpenSSL_ and `service_identity`_ for the actual SSL work.

Is the API stable?
------------------

Probably not.  However, it is currently very simple, so it shouldn't be hard to
upgrade code if there's a non backwards-compatible change.

Do I need to initialize `Crochet`_?
-----------------------------------

No, `crochet.setup`_ is automatically invoked by :py:func:`fido.fetch`.

How do I use an http_proxy?
---------------------------

Just set the http_proxy (all lowercase) environment variable to the URL of
the http proxy before starting your python process.

Example::

    $ export http_proxy="http://localhost:8000"
    $ python -c "import fido; print fido.fetch("http://www.example.com").wait().body


API
===

.. currentmodule:: fido

.. autofunction:: fetch

.. autoclass:: Response
  :members: json

.. _Crochet: https://github.com/itamarst/crochet
.. _crochet.setup: https://crochet.readthedocs.org/en/latest/api.html#setup
.. _Twisted: https://twistedmatrix.com/trac/
.. _concurrent.futures: http://pythonhosted.org/futures/
.. _ThreadPoolExecutor: http://pythonhosted.org/futures/#threadpoolexecutor-objects
.. _pyOpenSSL: https://github.com/pyca/pyopenssl
.. _service_identity: https://github.com/pyca/service_identity
