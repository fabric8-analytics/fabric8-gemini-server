#!/usr/bin/env python3

"""Project setup file for the analytics server project."""

from setuptools import setup, find_packages


def get_requirements():
    """
    Parse dependencies from 'requirements.in' file.

    Collecting dependencies from 'requirements.in' as a list,
    this list will be used by 'install_requires' to specify minimal dependencies
    needed to run the application.
    """
    with open('requirements.in') as fd:
        return fd.read().splitlines()


# pip doesn't install from dependency links by default, so one should install dependencies by
#  `pip install -r requirements.txt`, not by `pip install .`
#  See https://github.com/pypa/pip/issues/2023
install_requires = get_requirements()

setup(
    name='gemini-server',
    version='0.1',
    packages=find_packages(exclude=['tests', 'tests.*']),
    install_requires=install_requires,
    include_package_data=True,
    author='Samuzzal Choudhury',
    author_email='samuzzal@redhat.com',
    description='fabric8-analytics Gemini API Server',
    license='GPLv3',
    keywords='fabric8 analytics Gemini Server',
    url='https://github.com/fabric8-analytics/fabric8-gemini-server'
)
