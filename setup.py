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
    install_requires=[
        'crochet',
        'service_identity',
        'six',
        'pyOpenSSL',
    ],
    extras_require={
        ':python_version!="2.6"': ['twisted >= 14.0.0'],
        ':python_version=="2.6"': ['twisted >= 14.0.0, < 15.5', 'futures'],
        ':python_version=="2.7"': ['futures'],
    },
    license=about['__license__'],
)
