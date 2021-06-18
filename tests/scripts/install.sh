#!/bin/bash
CI_SYSTEM=${1}
PYTHON_MAJOR_VERSION=${2}
PYTHON_MINOR_VERSION=${3}

if [ ${CI_SYSTEM} == "TRAVIS" ]; then
    PYTHON_VERSION=${PYTHON_MAJOR_VERSION}
else
    if [ ! -z $PYTHON_MAJOR_VERSION ]; then
        PYTHON_VERSION=${PYTHON_MAJOR_VERSION}
    fi

    if [ ! -z $PYTHON_MAJOR_VERSION ] && [ ! -z $PYTHON_MINOR_VERSION ]; then
        PYTHON_VERSION=${PYTHON_VERSION}"."${PYTHON_MINOR_VERSION}
    fi
fi

pip${PYTHON_VERSION} install -e ./[tests]
pip${PYTHON_VERSION} install -e ./[docs]
pip${PYTHON_VERSION} install sftpserver

