"""Utility classes and functions."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from f8a_worker.models import OSIORegisteredRepos
from selinon import run_flow
import datetime
import requests
import os
import logging


logger = logging.getLogger(__name__)

GREMLIN_SERVER_URL_REST = "http://{host}:{port}".format(
    host=os.environ.get("BAYESIAN_GREMLIN_HTTP_SERVICE_HOST", "localhost"),
    port=os.environ.get("BAYESIAN_GREMLIN_HTTP_SERVICE_PORT", "8182"))

LICENSE_SCORING_URL_REST = "http://{host}:{port}".format(
    host=os.environ.get("LICENSE_SERVICE_HOST"),
    port=os.environ.get("LICENSE_SERVICE_PORT"))


class Postgres:
    """Postgres utility class to create postgres connection session."""

    def __init__(self):
        """Postgres utility class constructor."""
        self.connection = "postgresql://{user}:{password}@ \
                            {pgbouncer_host}:{pgbouncer_port}' \
                          '/{database}?sslmode=disable". \
            format(user=os.getenv('POSTGRESQL_USER'),
                   password=os.getenv('POSTGRESQL_PASSWORD'),
                   pgbouncer_host=os.getenv('PGBOUNCER_SERVICE_HOST',
                   'bayesian-pgbouncer'),
                   pgbouncer_port=os.getenv('PGBOUNCER_SERVICE_PORT', '5432'),
                   database=os.getenv('POSTGRESQL_DATABASE'))

        engine = create_engine(self.connection)

        self.Session = sessionmaker(bind=engine)
        self.session = self.Session()

    def session(self):
        """Postgres utility session getter."""
        return self.session


_rdb = Postgres()
_session = _rdb.session


def get_session_retry(retries=3, backoff_factor=0.2,
                      status_forcelist=(404, 500, 502, 504),
                      session=None):
    """Set HTTP Adapter with retries to session."""
    session = session or requests.Session()
    retry = Retry(total=retries, read=retries,
                  connect=retries,
                  backoff_factor=backoff_factor,
                  status_forcelist=status_forcelist)

    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    return session


def validate_request_data(input_json):
    validate_string = "{} cannot be empty"
    if 'git_url' not in input_json:
        validate_string = validate_string.format("git_url")
        return False, validate_string

    if 'git_sha' not in input_json:
        validate_string = validate_string.format("git_sha")
        return False, validate_string

    if 'email_ids' not in input_json:
        validate_string = validate_string.format("email_ids")
        return False, validate_string

    return True, None


def persist_repo_in_db(data):
    """Store registered repository in the postgres database."""
    req = OSIORegisteredRepos(
            git_url=data['git_url'],
            git_sha=data['git_sha'],
            email_ids=data['email_ids'],
            last_scanned_at=datetime.datetime.now()
            )
    try:
        #Work in progress
        #req is not of tyoe sql alchemy instead is of type f8a_worker

        check_existing = _session.query(req)

        if not check_existing():

            req = OSIORegisteredRepos(
            git_url=data['git_url'],
            git_sha=data['git_sha'],
            email_ids=data['email_ids'],
            last_scanned_at=datetime.datetime.now()
            )

            _session.add(req)
        else:
            req = {
                "git_url":data['git_url'],
                "git_sha":data['git_sha'],
                "email_ids":data['email_ids'],
                "last_scanned_at":datetime.datetime.now()
                }
            _session.query(req)
            _session.query(OSIORegisteredRepos).filter_by(data["git_url"]).update(req)

        _session.commit()
    except SQLAlchemyError as e:
        message = 'persisting records in the database failed. {}.'.format(e)
        logger.exception(message)
        return False

    return True


def scan_repo(data):
    """Scan function."""
    return True


class worker_selinon_flow:

    def __init__(self):
        init_selinon()

    def server_run_flow(self, flow_name, flow_args):
        """Run a flow.
        :param flow_name: name of flow to be run as stated in YAML config file
        :param flow_args: arguments for the flow
        :return: dispatcher ID handling flow
        """
        current_app.logger.debug('Running flow {}'.format(flow_name))
        start = datetime.datetime.now()

        init_celery(result_backend=False)
        dispacher_id = run_flow(flow_name, flow_args)

        elapsed_seconds = (datetime.datetime.now() - start).total_seconds()
        current_app.logger.debug("It took {t} seconds to start {f} flow.".format(
            t=elapsed_seconds, f=flow_name))
        return dispacher_id


    #To integrate with Aagams workflow
    # def server_create_component_analyses(self, ecosystem, name, version, user_profile):
    #     """Run the component analysis for given ecosystem+package+version."""
    #     args = {
    #         'external_request_id': uuid.uuid4().hex,
    #         'data': {
    #             'api_name': 'component_analyses',
    #             'user_email': get_user_email(user_profile),
    #             'user_profile': user_profile,
    #             'request': {'ecosystem': ecosystem, 'name': name, 'version': version}
    #         }
    #     }
    #     return self.server_run_flow('componentApiFlow', args)

