#!/bin/bash
PATH=$PATH:~/.local/bin

pip3 install --user coveralls pytest-cov paramiko > /dev/null
py.test --cov redexpect --cov-config .coveragerc
coverage html
# coveralls
