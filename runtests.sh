#!/usr/bin/bash -ex

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
echo "Create Virtualenv for Python deps ..."
function prepare_venv() {
    VIRTUALENV=`which virtualenv`
    if [ $? -eq 1 ]; then   
        # python34 which is in CentOS does not have virtualenv binary
        VIRTUALENV=`which virtualenv-3`
    fi
    ${VIRTUALENV} -p python3 venv && source venv/bin/activate
}
prepare_venv
pip3 install -r requirements.txt
pip3 install git+https://github.com/fabric8-analytics/fabric8-analytics-worker.git@561636c

export DEPLOYMENT_PREFIX="${USER}"
export WORKER_ADMINISTRATION_REGION=api
export SENTRY_DSN=''
export PYTHONDONTWRITEBYTECODE=1
export POSTGRESQL_USER='coreapi'
export POSTGRESQL_PASSWORD='coreapipostgres'
export POSTGRESQL_DATABASE='coreapi'
export PGBOUNCER_SERVICE_HOST='0.0.0.0'

psql_conn_str="postgres://${POSTGRESQL_USER}:${POSTGRESQL_PASSWORD}@${PGBOUNCER_SERVICE_HOST}:${5432}/${POSTGRESQL_DATABASE}"
for i in {1..60}; do
    rc=`psql -q "${psql_conn_str}" -c ''; echo $?`
    [ "$rc" == "0" ] && break
    sleep 1
done;

python3 `which pytest` --cov=src/ --cov-report term-missing -vv tests/

rm -rf venv/
