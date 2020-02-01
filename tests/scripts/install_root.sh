#!/bin/bash
CI_SYSTEM=${1}
PYTHON_MAJOR_VERSION=${2}
PYTHON_MINOR_VERSION=${3}

if [ ${CI_SYSTEM} == "TRAVIS" ]; then
    PYTHON_VERSION=${PYTHON_MAJOR_VERSION}
else
    if [ ! -z PYTHON_MAJOR_VERSION ]; then
        PYTHON_VERSION=${PYTHON_MAJOR_VERSION}
    fi

    if [ ! -z PYTHON_MAJOR_VERSION ] && [ ! -z PYTHON_MINOR_VERSION ]; then
        PYTHON_VERSION=${PYTHON_VERSION}"."${PYTHON_MINOR_VERSION}
    fi
fi

apt update
apt install -y make curl wget openssh-client openssh-server git cmake libssl-dev zlib1g-dev

# Travis takes care of all the python deps
if [ -n CI_SYSTEM ] && [ CI_SYSTEM != "TRAVIS" ]; then
    apt install -y python${PYTHON_VERSION} python${PYTHON_VERSION}-dev
    apt install -y python${PYTHON_VERSION}-distutils || true
    wget -O get-pip.py https://bootstrap.pypa.io/get-pip.py
    python${PYTHON_VERSION} ./get-pip.py
fi

if [ -n CI_SYSTEM ] && [ CI_SYSTEM == "GITLAB" ]; then
    sed 's@session\s*required\s*pam_loginuid.so@session optional pam_loginuid.so@g' -i /etc/pam.d/sshd
    echo "export VISIBLE=now" >> /etc/profile
    source /etc/profile
    mkdir /var/run/sshd || true
    chmod 755 /builds /builds/Red_M
fi

if [ -n CI_SYSTEM ]; then
    mkdir /run/sshd || true
fi
