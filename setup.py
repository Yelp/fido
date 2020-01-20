from __future__ import absolute_import, division, print_function

import os

from setuptools import find_packages, setup

base_dir = os.path.dirname(__file__)

about = {}
with open(os.path.join(base_dir, "fido", "__about__.py")) as f:
    exec(f.read(), about)

setup(
    name=about['__title__'],
    version=about['__version__'],

    description=about['__summary__'],

    url=about['__uri__'],

    author=about['__author__'],
    author_email=about['__email__'],
    packages=find_packages(exclude=["tests", "tests.*"]),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
    ],
    install_requires=[
        'crochet',
        'six',
        'yelp_bytes',
    ],
    extras_require={
        'tls': [
            # Bug in pip's resolution of extras of extras is broken
            # so we list twisted[tls] out manually
            # see https://github.com/pypa/pip/issues/988
            'pyOpenSSL >= 16.0.0',
            'service-identity',
            'idna >= 0.6, != 2.3',
        ],

        # Defining twisted dependency here to allow twisted
        # requirement constraint defined by python_version
        '': ['twisted >= 14.0.0'],
        # Twisted>=17 does support only python 2.7 and 3.5+
        ':python_version=="3.3"': ['twisted < 17.0.0'],
        ':python_version=="3.4"': ['twisted < 17.0.0'],
    },
    license=about['__license__'],
)
