#!/usr/bin/env python
# coding: utf-8

import re
import setuptools
from setuptools import find_packages, setup

install_requires = []
dependency_links = []
package_data = {}

with open('requirements.txt') as f:
    requirements = f.read()


for line in re.split('\n', requirements):
    if line and line[0] == '#' and '#egg=' in line:
        line = re.search(r'#\s*(.*)', line).group(1)
    if line and line[0] != '#':
        install_requires.append(line)


package_data = {
    '': ['Makefile', '*.md', 'requirements.txt']
}


if __name__ == '__main__':

    setup(
        name='docker-record',
        version='0.0.3',
        description='',
        author='Jürgen Cito, Waldemar Hummer',
        author_email='cito@ifi.uzh.ch, waldemar.hummer@gmail.com',
        url='https://github.com/citostyle/docker-record',
        scripts=['bin/docker-record'],
        packages=find_packages(exclude=("tests", "tests.*")),
        package_data=package_data,
        install_requires=install_requires,
        dependency_links=dependency_links,
        test_suite="tests",
        license="Apache License 2.0",
        zip_safe=False,
        classifiers=[
            "Programming Language :: Python :: 2",
            "Programming Language :: Python :: 2.6",
            "Programming Language :: Python :: 2.7",
            "Programming Language :: Python :: 3",
            "Programming Language :: Python :: 3.3",
            "License :: OSI Approved :: Apache Software License"
        ]
    )
