"""Utility classes and functions."""
from flask import current_app
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm.exc import NoResultFound
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from f8a_worker.models import OSIORegisteredRepos, WorkerResult
from f8a_worker.setup_celery import init_celery
from selinon import run_flow
from parsers.maven_parser import MavenParser
from parsers.node_parser import NodeParser
import datetime
import requests
import os
import logging
import boto3
import json
import re
import psycopg2
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

GREMLIN_SERVER_URL_REST = "http://{host}:{port}".format(
    host=os.environ.get("BAYESIAN_GREMLIN_HTTP_SERVICE_HOST", "localhost"),
    port=os.environ.get("BAYESIAN_GREMLIN_HTTP_SERVICE_PORT", "8182"))

LICENSE_SCORING_URL_REST = "http://{host}:{port}".format(
    host=os.environ.get("LICENSE_SERVICE_HOST"),
    port=os.environ.get("LICENSE_SERVICE_PORT"))


def sanitize_text_for_query(text):
    """
    Sanitize text so it can used in queries.

    :param text: string, text to sanitize
    :return: sanitized text
    """
    if text is None:
        return ''

    if not isinstance(text, str):
        raise ValueError(
            'Invalid query text: expected string, got {t}'.format(t=type(text))
        )

    strict_check_words = ['drop', 'delete', 'update', 'remove', 'insert']
    if re.compile('|'.join(strict_check_words), re.IGNORECASE).search(text):
        raise ValueError('Only select queries are supported')

    # remove newlines, quotes and backslash character
    text = " ".join([line.strip() for line in text.split("\n")])
    return text.strip()


class GraphPassThrough:
    """Graph database pass through handler."""

    def fetch_nodes(self, data):
        """Fetch node from graph database."""
        if data and data.get('query'):
            try:
                # sanitize the query to drop CRUD operations
                query = sanitize_text_for_query(data['query'])
                if query:
                    payload = {'gremlin': query}
                    resp = requests.post(url=GREMLIN_SERVER_URL_REST, json=payload)
                    return {'data': resp.json()}
            except (ValueError, requests.exceptions.Timeout, Exception) as e:
                return {'error': str(e)}
        else:
            return {'warning': 'Invalid payload. Check your payload once again'}


class PostgresPassThrough:
    """Postgres connection pass through session and cursor handler."""

    def __init__(self):
        """Initialize the connection to Postgres database using psycopg2 as a pass through."""
        self.conn_string = "host='{host}' dbname='{dbname}' user='{user}' password='{password}'".\
            format(host=os.getenv('PGBOUNCER_SERVICE_HOST', 'bayesian-pgbouncer'),
                   dbname=os.getenv('POSTGRESQL_DATABASE', 'coreapi'),
                   user=os.getenv('POSTGRESQL_USER', 'coreapi'),
                   password=os.getenv('POSTGRESQL_PASSWORD', 'coreapi'))

    def fetch_records(self, data):
        """Fetch records from RDS database."""
        if data and data.get('query'):
            try:
                conn = psycopg2.connect(self.conn_string)
                cursor = conn.cursor()
                # sanitize the query to drop CRUD operations
                query = sanitize_text_for_query(data['query'])
                if query:
                    cursor.execute(query)
                    return {'data': cursor.fetchmany(10)}
            except (ValueError, Exception) as e:
                return {'error': str(e)}
            finally:
                conn.commit()
                cursor.close()
                conn.close()
        else:
            return {'warning': 'Invalid payload. Check your payload once again'}


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


class S3Helper:
    """Helper class for storing reports to S3."""

    def __init__(self):
        """Init method for the helper class."""
        self.region_name = os.environ.get('AWS_S3_REGION') or 'us-east-1'
        self.aws_s3_access_key = os.environ.get('AWS_S3_ACCESS_KEY_ID')
        self.aws_s3_secret_access_key = os.environ.get('AWS_S3_SECRET_ACCESS_KEY')
        self.deployment_prefix = os.environ.get('DEPLOYMENT_PREFIX') or 'dev'
        if self.deployment_prefix not in ('STAGE', 'prod'):
            self.deployment_prefix = 'dev'

        if self.aws_s3_secret_access_key is None or self.aws_s3_access_key is None or\
                self.region_name is None or self.deployment_prefix is None:
            raise ValueError("AWS credentials or S3 configuration was "
                             "not provided correctly. Please set the AWS_S3_REGION, "
                             "AWS_S3_ACCESS_KEY_ID, AWS_S3_SECRET_ACCESS_KEY, REPORT_BUCKET_NAME "
                             "and DEPLOYMENT_PREFIX correctly.")
        # S3 endpoint URL is required only for local deployments
        self.s3_endpoint_url = os.environ.get('S3_ENDPOINT_URL') or 'http://localhost'

        self.s3 = boto3.resource('s3', region_name=self.region_name,
                                 aws_access_key_id=self.aws_s3_access_key,
                                 aws_secret_access_key=self.aws_s3_secret_access_key)
        self.s3_bucket_obj = self.s3.Bucket(os.environ.get('REPORT_BUCKET_NAME'))

    def list_objects(self, loc_prefix='weekly'):
        """Fetch the list of objects found on the S3 bucket."""
        prefix = '{loc_prefix}'.format(loc_prefix=loc_prefix)
        res = {'objects': []}
        for obj in self.s3_bucket_obj.objects.filter(Prefix=prefix):
            if os.path.basename(obj.key) != '':
                res['objects'].append(obj.key)
        return res

    def get_object_content(self, object_name):
        """Get the report json object found on the S3 bucket."""
        obj = self.s3.Object(os.environ.get('REPORT_BUCKET_NAME'), object_name)
        try:
            result = json.loads(obj.get()['Body'].read().decode('utf-8'))
        except ClientError as e:
            logger.error('Exception found: %r' % e)
            raise e
        return result


_s3_helper = S3Helper()


def query_worker_result(session, external_request_id, worker):  # pragma: no cover
    """Query worker_result table."""
    return session.query(WorkerResult) \
        .filter(WorkerResult.external_request_id == external_request_id,
                WorkerResult.worker == worker) \
        .order_by(WorkerResult.ended_at.desc())


def get_first_query_result(query):  # pragma: no cover
    """Return first result of query."""
    return query.first()


def retrieve_worker_result(external_request_id, worker):
    """Retrieve results for selected worker from RDB."""
    start = datetime.datetime.now()
    session = get_session()
    try:
        query = query_worker_result(session, external_request_id, worker)
        result = get_first_query_result(query)
    except SQLAlchemyError:
        session.rollback()
        raise

    if result:
        result_dict = result.to_dict()
        elapsed_seconds = (datetime.datetime.now() - start).total_seconds()
        msg = "It took {t} seconds to retrieve {w} " \
            "worker results for {r}.".format(t=elapsed_seconds, w=worker, r=external_request_id)
        current_app.logger.debug(msg)

        return result_dict

    return None


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

    :param input_json: dict, describing data
    :return: boolean, result
    """
    validate_string = "{} cannot be empty"
    if 'git-url' not in input_json:
        validate_string = validate_string.format("git-url")
        return False, validate_string

    if 'git-sha' not in input_json:
        validate_string = validate_string.format("git-sha")
        return False, validate_string

    return True, None


def _to_object_dict(data):  # pragma: no cover
    """Convert the object of type JobToken into a dictionary."""
    return_dict = {OSIORegisteredRepos.git_url: data["git-url"],
                   OSIORegisteredRepos.git_sha: data["git-sha"],
                   OSIORegisteredRepos.email_ids: data.get('email-ids', 'dummy'),
                   OSIORegisteredRepos.last_scanned_at: datetime.datetime.now()
                   }
    return return_dict


def update_osio_registered_repos(session, data):  # pragma: no cover
    """Update osio_registered_repos table."""
    session.query(OSIORegisteredRepos). \
        filter(OSIORegisteredRepos.git_url == data["git-url"]). \
        update(_to_object_dict(data))


def add_entry_to_osio_registered_repos(session, entry):  # pragma: no cover
    """Add single entry to osio_registered_repos table."""
    session.add(entry)


def get_one_result_from_osio_registered_repos(session, search_key):  # pragma no cover
    """Get one result from osio_registered_repos table."""
    return session.query(OSIORegisteredRepos) \
        .filter(OSIORegisteredRepos.git_url == search_key).one()


class DatabaseIngestion:
    """Class to ingest data into Database."""

    @staticmethod
    def update_data(data):
        """Update existing record in the database.

        :param data: dict, describing github data
        :return: None
        """
        try:
            session = get_session()
            update_osio_registered_repos(session, data)
            session.commit()
        except NoResultFound:
            raise Exception("Record trying to update does not exist")
        except SQLAlchemyError:
            session.rollback()
            raise Exception("Error in updating data")

    @classmethod
    def store_record(cls, data):
        """Store new record in the database.

        :param data: dict, describing github data
        :return: boolean based on completion of process
        """
        git_url = data.get("git-url", None)
        if git_url is None:
            logger.info("github Url not found")
            raise Exception("github Url not found")
        try:
            session = get_session()
            entry = OSIORegisteredRepos(
                git_url=data['git-url'],
                git_sha=data['git-sha'],
                email_ids=data.get('email-ids', 'dummy'),
                last_scanned_at=datetime.datetime.now()
            )
            add_entry_to_osio_registered_repos(session, entry)
            session.commit()
        except SQLAlchemyError:
            session.rollback()
            raise Exception("Error in storing the record in current session")
        except Exception as e:
            raise Exception("Error in storing the record due to {}".format(e))
        return cls.get_info(data["git-url"])

    @classmethod
    def get_info(cls, search_key):
        """Get information about github url.

        :param search_key: github url to search database
        :return: record from database if exists
        """
        if not search_key:
            return {'error': 'No key found', 'is_valid': False}

        session = get_session()

        try:
            entry = get_one_result_from_osio_registered_repos(
                session, search_key)
        except NoResultFound:
            logger.info("No info for search_key '%s' was found", search_key)
            return {'error': 'No information in the records', 'is_valid': False}
        except SQLAlchemyError:
            session.rollback()
            raise Exception("Error in retrieving the record in current session")
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
    args = {'github_repo': data['git-url'],
            'github_sha': data['git-sha'],
            'email_ids': data.get('email-ids', 'dummy')}
    d_id = server_run_flow('osioAnalysisFlow', args)
    logger.info("DISPATCHER ID = {}".format(d_id))
    return True


def alert_user(data, service_token="", epv_list=[]):
    """Invoke worker flow to scan user repository."""
    args = {'github_repo': data['git-url'],
            'service_token': service_token,
            'email_ids': data.get('email-ids', 'dummy'),
            'epv_list': epv_list}

    d_id = server_run_flow('osioUserNotificationFlow', args)
    logger.info("DISPATCHER ID = {}".format(d_id))
    return True


def fetch_public_key(app):
    """Get public key and caches it on the app object for future use."""
    # TODO: even though saving the key on the app object is not very nice,
    #  it's actually safe - the worst thing that can happen is that we will
    #  fetch and save the same value on the app object multiple times
    if not getattr(app, 'public_key', ''):
        keycloak_url = os.getenv('BAYESIAN_FETCH_PUBLIC_KEY', '')
        if keycloak_url:
            pub_key_url = keycloak_url.strip('/') + '/auth/realms/fabric8/'
            try:
                result = requests.get(pub_key_url, timeout=0.5)
                app.logger.info('Fetching public key from %s, status %d, result: %s',
                                pub_key_url, result.status_code, result.text)
            except requests.exceptions.Timeout:
                app.logger.error('Timeout fetching public key from %s', pub_key_url)
                return ''
            if result.status_code != 200:
                return ''
            pkey = result.json().get('public_key', '')
            app.public_key = \
                '-----BEGIN PUBLIC KEY-----\n{pkey}\n-----END PUBLIC KEY-----'.format(pkey=pkey)
        else:
            app.public_key = None

    return app.public_key


def fix_gremlin_output(response):
    """Reshuffle data in the response from Gremlin for easier access later.

    :param response: dict, response from Gremlin
    :return dict: the same response dict with reshuffled data
    """
    if not response:
        return response

    data_list = response.get('result', {}).get('data', [])
    new_data = {}
    for data in data_list:
        cve = data.pop('cve')
        rp = data.get('rp', {})
        epv = data.get('epv', {})
        ed = data.get('ed', {})
        pv = epv.get('pname')[0], epv.get('version')[0]

        d = new_data.get(pv, {})
        d['rp'] = dict(d.get('rp', {}), **rp)
        d['ed'] = dict(d.get('ed', {}), **ed)
        d['epv'] = dict(d.get('epv', {}), **epv)
        d['cves'] = d.get('cves', []) + [cve]
        new_data[pv] = d
    response['result']['data'] = new_data.values()

    return response


def get_parser_from_ecosystem(ecosystem):
    """Get parser for the provided ecosystem."""
    return {
        "maven": MavenParser,
        "npm": NodeParser
    }.get(ecosystem)


def generate_comparison(comparison_days):
    """Generate comparioson report."""
    today = datetime.datetime.today()
    i = 0
    response_times = []
    dp = os.environ.get('DEPLOYMENT_PREFIX') or 'dev'
    while i < comparison_days:
        formatted_date = (today - datetime.timedelta(days=i + 1)).strftime('%Y-%m-%d')
        logger.error('Formatted Date: {}'.format(formatted_date))

        report_name = '{dp}/daily/{cdate}.json'.format(dp=dp, cdate=formatted_date)
        logger.error('Report Name: {}'.format(report_name))

        missing_reports = 0
        try:
            data = _s3_helper.get_object_content(report_name)
        except ClientError as e:
            if comparison_days == 2:
                logger.error('the report for {} is missing. Cannot proceed with the '
                             'comparison. Error: {}'.format(formatted_date, e))
                return -1
            else:
                missing_reports += 1
                if comparison_days - missing_reports == 1:
                    logger.error('Insufficient reports to generate comparison result')
                    return -1
                continue
        response_times.append({formatted_date: data.get('stacks_summary', {}).
                              get('total_average_response_time')})
        i += 1

    logger.error('Average Response Time: %r' % response_times)
    return {"average_response_time": response_times}
