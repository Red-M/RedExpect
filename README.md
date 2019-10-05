# RedExpect
[![Documentation Status](https://readthedocs.org/projects/redexpect/badge/?version=latest)](https://redexpect.readthedocs.io/en/latest/?badge=latest)

RedExpect makes automating remote machines over SSH very easy to do and is very fast in doing exactly what you ask of it.
Based on ssh2-python (which provides libssh2 bindings for python) and made into an easy to use SSH library via RedSSH.
If you're familiar with using expect but would like the easy of use and accessibilty of python, then look no further!


# Installing

RedExpect can be installed via pip with `pip install redexpect` or the latest commit, which may not be the most stable, from git with `pip install git://git@bitbucket.org/Red_M/RedExpect.git`


# Documentation
99% of questions around how to do something should be answered in the documentation.
If something is not there please raise an issue so it can be added to the documentation.
[Now with autodocs!](https://redexpect.readthedocs.io/en/latest/ "Documentation! :)")


# Why not use [other software]?

I've found other automation libraries or solutions lacking, such as:
- Compatibility with remote servers (odd servers causes the library to be unable to connect).
- Feature set is limited (eg, no tunneling).
- Focuses on only connecting to Linux servers.
- Requires an agent to be installed, a state file to be present or a master "server".
- Poor performance.


# TO DO
- Unit tests
- More examples
