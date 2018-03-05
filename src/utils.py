"""Utility classes and functions."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm.exc import NoResultFound
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from f8a_worker.models import OSIORegisteredRepos
from f8a_worker.setup_celery import init_celery
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
        con_string = 'postgresql://{user}' + ':{passwd}@{pg_host}:' \
            + '{pg_port}/{db}?sslmode=disable'

        self.connection = con_string.format(
            user=os.getenv('POSTGRESQL_USER'),
            passwd=os.getenv('POSTGRESQL_PASSWORD'),
            pg_host=os.getenv(
                'PGBOUNCER_SERVICE_HOST',
                'bayesian-pgbouncer'),
            pg_port=os.getenv(
                'PGBOUNCER_SERVICE_PORT',
                '5432'),
            db=os.getenv('POSTGRESQL_DATABASE'))
        engine = create_engine(self.connection)

        self.Session = sessionmaker(bind=engine)
        self.session = self.Session()

    def session(self):
        """Postgres utility session getter."""
        return self.session


_rdb = Postgres()


def get_session():
    """Retrieve the database connection session."""
    try:
        session = _rdb.session
    except Exception as e:
        raise Exception("session could not be loaded due to {}".format(e))
    return session


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
    """Validate the data.

    :param data: dict, describing data
    :return: boolean, result
    """
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


def _to_object_dict(data):
    """Convert the object of type JobToken into a dictionary."""
    return_dict = {OSIORegisteredRepos.git_url: data["git_url"],
                   OSIORegisteredRepos.git_sha: data["git_sha"],
                   OSIORegisteredRepos.email_ids: data["email_ids"],
                   OSIORegisteredRepos.last_scanned_at: datetime.datetime.now()
                   }
    return return_dict


class DatabaseIngestion():
    """Class to ingest data into Database."""

    @staticmethod
    def _update_data(session, data):
        try:
            entries = session.query(OSIORegisteredRepos).\
                filter(OSIORegisteredRepos.git_url == data["git_url"]).\
                update(_to_object_dict(data))
            session.commit()
        except NoResultFound:
            raise Exception("Record trying to update doesnot exist")
        except SQLAlchemyError:
            session.rollback()
            raise Exception("Error in updating data")

    @classmethod
    def store_record(cls, data):
        """Store new record and update old ones.

        :param data: dict, describing github data
        :return: boolean based on completion of process
        """
        git_url = data.get("git_url", None)
        if git_url is None:
            logger.info("github Url not found")
            raise Exception("github Url not found")
        try:
            session = get_session()
            check_existing = cls.get_info(git_url)
            if check_existing["is_valid"]:
                cls._update_data(session, data)
                return check_existing["data"]

            entry = OSIORegisteredRepos(
                git_url=data['git_url'],
                git_sha=data['git_sha'],
                email_ids=data['email_ids'],
                last_scanned_at=datetime.datetime.now()
            )
            session.add(entry)
            session.commit()
        except SQLAlchemyError:
            session.rollback()
            raise Exception("Error in storing the record in current session")
        except Exception as e:
            raise Exception("Error in storing the record due to {}".format(e))
        return cls.get_info(data["git_url"])

    @classmethod
    def get_info(cls, search_key):
        """Get information about github url.

        :param search_key: github url to serach database
        :return: record from database if exists
        """
        if not search_key:
            return {'error': 'No key found', 'is_valid': False}

        session = get_session()

        try:
            entry = session.query(OSIORegisteredRepos) \
                    .filter(OSIORegisteredRepos.git_url == search_key).one()
        except NoResultFound:
            logger.info("No info for search_key '%s' was found", search_key)
            return {'errnoror': 'No information in the records', 'is_valid': False}
        except SQLchemyError:
            session.rollback()
            raise
        except Exception as e:
            raise {
                  'error': 'Error in getting info due to {}'.format(e),
                  'is_valid': False
            }

        return {'is_valid': True, 'data': entry.to_dict()}


def server_run_flow(flow_name, flow_args):
    """Run a flow.

    :param flow_name: name of flow to be run as stated in YAML config file
    :param flow_args: arguments for the flow
    :return: dispatcher ID handling flow
    """
    logger.info('Running flow {}'.format(flow_name))
    start = datetime.datetime.now()

    init_celery(result_backend=False)
    dispacher_id = run_flow(flow_name, flow_args)

    elapsed_seconds = (datetime.datetime.now() - start).total_seconds()
    logger.info("It took {t} seconds to start {f} flow.".format(
        t=elapsed_seconds, f=flow_name))
    return dispacher_id


def scan_repo(data):
    """Scan function."""
    args = {'github_repo': data['git_url'],
            'github_sha': data['git_sha'],
            'email_ids': data['email_ids']}
    d_id = server_run_flow('osioAnalysisFlow', args)
    logger.info("DISPATCHER ID = {}".format(d_id))
    return True
