#!/usr/bin/env python

import re
from setuptools import setup, find_packages

pkgname = 'pyworkflow'

# gather the package information
main_py = open('pyworkflow/__init__.py').read()
metadata = dict(re.findall("__([a-z]+)__ = '([^']+)'", main_py))
packages = filter(lambda p: p.startswith(pkgname), find_packages())

# convert the readme to pypi compatible rst
try:
  try:
    import pypandoc
    readme = pypandoc.convert('README.md', 'rst')
  except ImportError:
    readme = open('README.md').read()
except:
  print 'something went wrong reading the README.md file.'
  readme = ''

setup(
  name=pkgname,
  version=metadata['version'],
  description='unified API for workflow processes',
  long_description=readme,
  author=metadata['author'],
  author_email=metadata['email'],
  url='http://github.com/pyworkflow/pyworkflow',
  keywords=[
    'pyworkflow',
    'workflow',
    'unified api',
  ],
  packages=packages,
  test_suite='pyworkflow.test',
  license='MIT License',
  classifiers=[
    'Topic :: Database',
    'Topic :: Database :: Front-Ends',
  ]
)
