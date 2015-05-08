from __future__ import absolute_import, division, print_function

import os
import sys

from setuptools import find_packages, setup

base_dir = os.path.dirname(__file__)

about = {}
with open(os.path.join(base_dir, "fido", "__about__.py")) as f:
    exec(f.read(), about)

install_requires = [
    # TODO: Unpin twisted when https://twistedmatrix.com/trac/ticket/7888 is
    #       fixed. Specifically, twisted 15.1.0 causes the test_fetch_body
    #       unit test to fail.
    'twisted == 15.0.0',
    'crochet',
    'service_identity',
    'pyOpenSSL',
]

if sys.version_info < (3, 2):
    install_requires.append('futures')

setup(
    name=about['__title__'],
    version=about['__version__'],

    description=about['__summary__'],

    url=about['__uri__'],

    author=about['__author__'],
    author_email=about['__email__'],
    packages=find_packages(exclude=["tests", "tests.*"]),
    install_requires=install_requires,
    license=about['__license__']
)
