# -*- coding: utf-8 -*-
from setuptools import setup, find_namespace_packages
import os
from pyscada import sse as pyscada_app


CLASSIFIERS = [
    "Development Status :: 4 - Beta",
    "Environment :: Web Environment",
    "Environment :: Console",
    "Framework :: Django",
    "Intended Audience :: Developers",
    "Intended Audience :: Science/Research",
    "License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)",
    "Operating System :: POSIX",
    "Operating System :: MacOS :: MacOS X",
    "Programming Language :: Python",
    "Programming Language :: JavaScript",
    "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
    "Topic :: Scientific/Engineering :: Visualization",
]
setup(
    author=pyscada_app.__author__,
    author_email=pyscada_app.__email__,
    name="pyscada-" + pyscada_app.__app_name__.lower(),
    version=pyscada_app.__version__,
    description=pyscada_app.__description__,
    long_description=open(os.path.join(os.path.dirname(__file__), "README.rst")).read(),
    url="http://www.github.com/pyscada/PyScada-" + pyscada_app.__app_name__,
    license="AGPLv3",
    platforms=["OS Independent"],
    classifiers=CLASSIFIERS,
    install_requires=[
        "django>=5.1",
        "pyscada>=0.8.3",
        "django_eventstream>=5.1.0",
        "daphne",
        "Twisted[tls,http2]",
    ],
    packages=find_namespace_packages(exclude=["project", "project.*"]),
    include_package_data=True,
    zip_safe=False,
    test_suite="runtests.main",
)
