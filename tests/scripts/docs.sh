#!/bin/bash
CI_SYSTEM=${1}
PYTHON_VERSION=${2}


export PATH=$PATH:~/.local/bin

cd ./docs
mkdir build
mkdir ../public
ln -s ./build/html ../public
make html
