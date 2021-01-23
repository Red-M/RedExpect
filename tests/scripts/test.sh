#!/bin/bash
PATH=$PATH:~/.local/bin
CI_SYSTEM=${1}
PYTHON_VERSION=${2}

if [ ! -z $CI_SYSTEM ] && [ ${CI_SYSTEM} != "LOCAL" ]; then
    git checkout master
fi

if [ ! -z $CI_SYSTEM ] && [ ${CI_SYSTEM} == "TRAVIS" ]; then
    pip${PYTHON_VERSION} install --upgrade pytest coveralls pytest-cov pytest-xdist paramiko > /dev/null
    py.test --cov redexpect
else
    pip${PYTHON_VERSION} install --upgrade --user pytest coveralls pytest-cov pytest-xdist paramiko > /dev/null
    py.test --cov redexpect --cov-config .coveragerc
fi


coverage html
if [ ! -z $CI_SYSTEM ]; then
    coveralls || true
fi

CODE_VALIDATION_PY_FILES="$(find ./ -type f | grep '\.py$')"
BANDIT_REPORT=$(tempfile)
PYLINT_REPORT=$(tempfile)
echo "*********** Bandit ***********"
bandit -c ./.bandit.yml -r ${CODE_VALIDATION_PY_FILES} 2>&1 > "${BANDIT_REPORT}"
cat "${BANDIT_REPORT}"

echo "*********** Pylint ***********"
pylint ${CODE_VALIDATION_PY_FILES} 2>&1 > "${PYLINT_REPORT}"
cat "${PYLINT_REPORT}"
