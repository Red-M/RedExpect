# RedExpect
# Copyright (C) 2018 - 2020  Red_M ( http://bitbucket.com/Red_M )

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
import re
import setuptools

with open('README.md', 'r') as fh:
    long_description = fh.read()

with open('redexpect/__init__.py', 'r') as fh:
    reg = re.compile(r"^VERSION.+?\'(.*)\'$",re.DOTALL|re.MULTILINE)
    redexpect_version = reg.findall(fh.read())[0]

deps = [
    'redssh>=2.0.0'
]

doc_deps = [
    'sphinx',
    'sphinx_rtd_theme'
]

test_deps = [
    'redssh[tests]',
    'asyncssh',
    'paramiko',
    'sftpserver',
    'coveralls',
    'pytest-cov',
    'pylint',
    'bandit',
    'safety'
]

package_excludes = [
    'tests',
    'tests.*',
    '*.tests',
    '*.tests.*'
]


setuptools.setup(
    name='redexpect',
    version=redexpect_version,
    url='https://bitbucket.org/Red_M/RedExpect',
    license='GPLv2',
    author='Red_M',
    author_email='redexpect_pypi@red-m.net',
    description='An SSH automation library using expect.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    packages=setuptools.find_packages(exclude=package_excludes),
    platforms='Posix',
    install_requires=deps,
    extras_require={
        'tests':list(set(deps+test_deps)),
        'docs':list(set(deps+doc_deps))
    },
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: System :: Shells',
        'Topic :: System :: Networking',
        'Operating System :: POSIX',
        'Operating System :: POSIX :: Linux',
        'Operating System :: POSIX :: BSD',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: OS Independent'
    ],
)
