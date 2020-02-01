#!/bin/bash
CI_SYSTEM=${1}
PYTHON_MAJOR_VERSION=${2}
PYTHON_MINOR_VERSION=${3}

pip${PYTHON_VERSION} install -e ./[tests]
pip${PYTHON_VERSION} install -e ./[docs]
pip${PYTHON_VERSION} install sftpserver

