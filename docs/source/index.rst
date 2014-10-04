.. sprocket documentation master file, created by
   sphinx-quickstart on Fri May 13 14:16:02 2011.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Sprocket
********

Introduction
============

Sprocket is a simple, asynchronous HTTP client built on top of Crochet_,
Twisted_ and `concurrent.futures`_.  It is intended to be used in environments
where there is no event loop, and where you cannot afford to spin up lots of
threads (otherwise you could just use a `ThreadPoolExecutor`_).

Here is an example of using Sprocket::

    future = sprocket.fetch('http://www.yelp.com')
    # Work happens in a background thread...
    response = future.wait(timeout=2)
    print response.body

Frequently Asked Questions
==========================

Do you support SSL?
-------------------

Yes, but I don't know whether it's secure;  we should talk before you depend on
this functionality. In more detail: Sprocket uses the Twisted defaults,
which delegate to pyOpenSSL_ and `service_identity`_ for the actual SSL work.

Is the API stable?
------------------

Probably not.  However, it is currently very simple, so it shouldn't be hard to
upgrade code if there's a non backwards-compatible change.

Do I need to initialize `Crochet`_?
-----------------------------------

No, `crochet.setup`_ is automatically invoked by :py:func:`sprocket.fetch`.

API
===

.. currentmodule:: sprocket

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
