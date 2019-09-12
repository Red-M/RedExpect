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


# Why not use <other software>?

This is my experiences with other pieces of software to do something similar or the same as RedExpect.
It mostly revolves around compatibility with remote servers, (lack of) state(less) based automation or lack of features.

I've had issues with other software in the past and sometimes I found that other software doesn't want to do what I want it to do.
I should be able to open and close SSH tunnels at a whim, start up SCP/SFTP and access other lower level features of SSH at any time.

I've had issues with accessing non-Linux devices that have weird versions or custom compiles of the OpenSSH server or are completely custom SSH servers.
Because of incompatibility in other libraries, RedExpect isn't designed with just Linux in mind, its meant to control everything you can think of that has SSH.
If you can connect to it via your regular OpenSSH client then RedExpect/RedSSH should be able to connect as well.

I don't want to install an agent or have to manage state of a remote machine, if I want something done it should just be applied,
I don't want extra things to manage or leave hanging around.


# TO DO
- Unit tests
- More examples
