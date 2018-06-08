#!/usr/bin/bash -ex

COVERAGE_THRESHOLD=90

export TERM=xterm
TERM=${TERM:-xterm}

# set up terminal colors
NORMAL=$(tput sgr0)
RED=$(tput bold && tput setaf 1)
GREEN=$(tput bold && tput setaf 2)
YELLOW=$(tput bold && tput setaf 3)

printf "${NORMAL}Shutting down docker-compose ..."

gc() {
  retval=$?
  docker-compose -f docker-compose.yml down -v || :
  exit $retval
}
trap gc EXIT SIGINT

# Enter local-setup/ directory
# Run local instances for: dynamodb, gremlin-websocket, gremlin-http
function start_gemini_service {
    #pushd local-setup/
    echo "Invoke Docker Compose services"
    docker-compose -f docker-compose.yml up  --force-recreate -d
    #popd
}

start_gemini_service

export PYTHONPATH=`pwd`/src
printf "${NORMAL}Create Virtualenv for Python deps ..."

function prepare_venv() {
    VIRTUALENV=`which virtualenv`
    if [ $? -eq 1 ]
    then
        # python34 which is in CentOS does not have virtualenv binary
        VIRTUALENV=`which virtualenv-3`
    fi

    ${VIRTUALENV} -p python3 venv && source venv/bin/activate
    if [ $? -ne 0 ]
    then
        printf "${RED}Python virtual environment can't be initialized${NORMAL}"
        exit 1
    fi
}

prepare_venv

# now we are surely in the Python virtual environment

pip3 install -r requirements.txt
pip3 install git+https://github.com/fabric8-analytics/fabric8-analytics-worker.git@6f2c826

export DEPLOYMENT_PREFIX="${USER}"
export WORKER_ADMINISTRATION_REGION=api
export SENTRY_DSN=''
export PYTHONDONTWRITEBYTECODE=1
export POSTGRESQL_USER='coreapi'
export POSTGRESQL_PASSWORD='coreapipostgres'
export POSTGRESQL_DATABASE='coreapi'
export PGBOUNCER_SERVICE_HOST='0.0.0.0'
export DISABLE_AUTHENTICATION=1
export BAYESIAN_JWT_AUDIENCE='a,b'
export BAYESIAN_FETCH_PUBLIC_KEY='test'

psql_conn_str="postgres://${POSTGRESQL_USER}:${POSTGRESQL_PASSWORD}@${PGBOUNCER_SERVICE_HOST}:${5432}/${POSTGRESQL_DATABASE}"
for i in {1..60}; do
    rc=`psql -q "${psql_conn_str}" -c ''; echo $?`
    [ "$rc" == "0" ] && break
    sleep 1
done;

echo "*****************************************"
echo "*** Cyclomatic complexity measurement ***"
echo "*****************************************"
radon cc -s -a -i venv .

echo "*****************************************"
echo "*** Maintainability Index measurement ***"
echo "*****************************************"
radon mi -s -i venv .

echo "*****************************************"
echo "*** Unit tests ***"
echo "*****************************************"
python3 `which pytest` --cov=src/ --cov-report term-missing --cov-fail-under=$COVERAGE_THRESHOLD -vv tests/

# deactivate virtual env before deleting it
deactivate
rm -rf venv/
