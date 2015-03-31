#!/usr/bin/env python
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup
import sys

if sys.version_info >= (3, 4):
    install_requires = []
else:
    install_requires = ['asyncio']

setup(
        name='asyncio-redis-cluster',
        author='Renato Massaro',
        version='0.1',
        license='LICENSE.txt',
        url='https://github.com/hackerexperience/asyncio-redis-cluster',

        description='Cluster support for asyncio Redis client.',
        long_description=open("README.rst").read(),
        packages=['asyncio_redis_cluster'],
        install_requires=install_requires,
        extra_require = {
            'hiredis': ['hiredis'],
        }
)
