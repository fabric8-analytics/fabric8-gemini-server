from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import requests
import os
import logging
import json
import datetime
import semantic_version as sv

from f8a_worker.models import OSIORegisteredRepos

logger = logging.getLogger(__name__)

GREMLIN_SERVER_URL_REST = "http://{host}:{port}".format(
    host=os.environ.get("BAYESIAN_GREMLIN_HTTP_SERVICE_HOST", "localhost"),
    port=os.environ.get("BAYESIAN_GREMLIN_HTTP_SERVICE_PORT", "8182"))

LICENSE_SCORING_URL_REST = "http://{host}:{port}".format(
    host=os.environ.get("LICENSE_SERVICE_HOST"),
    port=os.environ.get("LICENSE_SERVICE_PORT"))


# Create Postgres Connection Session
class Postgres:
    def __init__(self):
        self.connection = 'postgresql://{user}:{password}@{pgbouncer_host}:{pgbouncer_port}' \
                          '/{database}?sslmode=disable'. \
            format(user=os.getenv('POSTGRESQL_USER'),
                   password=os.getenv('POSTGRESQL_PASSWORD'),
                   pgbouncer_host=os.getenv('PGBOUNCER_SERVICE_HOST', 'bayesian-pgbouncer'),
                   pgbouncer_port=os.getenv('PGBOUNCER_SERVICE_PORT', '5432'),
                   database=os.getenv('POSTGRESQL_DATABASE'))
        engine = create_engine(self.connection)

        self.Session = sessionmaker(bind=engine)
        self.session = self.Session()

    def session(self):
        return self.session


_rdb = Postgres()
_session = _rdb.session


def get_osio_user_count(ecosystem, name, version):
    str_gremlin = "g.V().has('pecosystem','{}').has('pname','{}').has('version','{}').".format(
        ecosystem, name, version)
    str_gremlin += "in('uses').count();"
    payload = {
        'gremlin': str_gremlin
    }

    try:
        response = get_session_retry().post(GREMLIN_SERVER_URL_REST, data=json.dumps(payload))
        json_response = response.json()
        return json_response['result']['data'][0]
    except Exception as e:
        logger.error("Failed retrieving Gremlin data.")
        logger.error("%r" % e)
        return -1


def get_session_retry(retries=3, backoff_factor=0.2, status_forcelist=(404, 500, 502, 504),
                      session=None):
    """Set HTTP Adapter with retries to session."""
    session = session or requests.Session()
    retry = Retry(total=retries, read=retries, connect=retries,
                  backoff_factor=backoff_factor, status_forcelist=status_forcelist)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    return session


def persist_repo_in_db(data):
    try:
        req = OSIORegisteredRepos(
            github_repo=data['github_repo'],
            github_sha=data['github_sha'],
            email_ids=data['email_ids']
        )
        _session.add(req)
        _session.commit()
    except SQLAlchemyError as e:
        message = 'persisting records in the database failed. {}.'.format(e)
        logger.exception(message)
        return {'message': message}

    return True


def scan_repo(data):
    return True
