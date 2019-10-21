"""Definition of the routes for gemini server."""
import flask
import os
import requests
from flask import Flask, request
from flask_cors import CORS
from utils import DatabaseIngestion, scan_repo, validate_request_data, \
    retrieve_worker_result, alert_user, GREMLIN_SERVER_URL_REST, _s3_helper, \
    generate_comparison
from f8a_worker.setup_celery import init_selinon
from fabric8a_auth.auth import login_required, init_service_account_token
from data_extractor import DataExtractor
from exceptions import HTTPError
from repo_dependency_creator import RepoDependencyCreator
from notification.user_notification import UserNotification
from fabric8a_auth.errors import AuthError
import sentry_sdk
from requests_futures.sessions import FuturesSession
import logging


app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
sentry_sdk.init(os.environ.get("SENTRY_DSN"))

init_selinon()
_session = FuturesSession(max_workers=3)

_SERVICE_HOST = os.environ.get("BAYESIAN_DATA_IMPORTER_SERVICE_HOST", "bayesian-data-importer")
_SERVICE_PORT = os.environ.get("BAYESIAN_DATA_IMPORTER_SERVICE_PORT", "9192")
_CVE_SYNC_ENDPOINT = "api/v1/sync_latest_non_cve_version"
_LATEST_VERSION_SYNC_ENDPOINT = "api/v1/sync_latest_version"
_CVE_SOURCE_SYNC_ENDPOINT = "api/v1/sync_cve_source"

SERVICE_TOKEN = 'token'
try:
    SERVICE_TOKEN = init_service_account_token(app)
except requests.exceptions.RequestException as e:
    print('Unable to set authentication token for internal service calls. {}'
          .format(e))


@app.route('/api/v1/readiness')
def readiness():
    """Readiness probe."""
    return flask.jsonify({}), 200


@app.route('/api/v1/liveness')
def liveness():
    """Liveness probe."""
    return flask.jsonify({}), 200


@app.route('/api/v1/sync-graph-data', methods=['POST'])
@login_required
def sync_data():
    """
    Endpoint for carrying a sync of graph db data.

    Takes in value to either call sync of non cve version
    or latest version or both.

    valid input: {
        "non_cve_sync": true/false,
        "latest_version_sync": true/false,
        "cve_ecosystem": ['maven', 'pypi, 'npm'],
        "cve_source_sync": {'cve_sources': 'CRA'}
    }

    """
    resp = {
        "success": True,
        "message": "Sync operation started ->"
    }

    input_json = request.get_json()
    logger.info("sync-graph-data called with the input {i}".format(i=input_json))
    non_cve_sync = input_json.get('non_cve_sync', False)
    if non_cve_sync:
        cve_ecosystem = input_json.get('cve_ecosystem', [])
        if len(cve_ecosystem) == 0:
            resp['success'] = False
            resp['message'] = "Incorrect data.. Send cve_ecosystem for non_cve_sync operation"
            logger.error("Incorrect data.. Send cve_ecosystem for non_cve_sync operation")
            return flask.jsonify(resp), 400
        url = "http://{host}:{port}/{endpoint}".format(host=_SERVICE_HOST,
                                                       port=_SERVICE_PORT,
                                                       endpoint=_CVE_SYNC_ENDPOINT)
        logger.info("Calling non cve sync with {i}".format(i=cve_ecosystem))
        _session.post(url, json=cve_ecosystem)
        resp['message'] = resp['message'] + " for non cve version"
    latest_version_sync = input_json.get('latest_version_sync', False)
    if latest_version_sync:
        url = "http://{host}:{port}/{endpoint}".format(host=_SERVICE_HOST,
                                                       port=_SERVICE_PORT,
                                                       endpoint=_LATEST_VERSION_SYNC_ENDPOINT)
        logger.info("Calling latest version sync with 'all'")
        _session.post(url, json=['all'])
        resp['message'] = resp['message'] + " for latest version"

    cve_source_sync = input_json.get('cve_source_sync', {})
    if cve_source_sync != {}:
        url = "http://{host}:{port}/{endpoint}".format(host=_SERVICE_HOST,
                                                       port=_SERVICE_PORT,
                                                       endpoint=_CVE_SOURCE_SYNC_ENDPOINT)
        logger.info("Calling latest cve source sync")
        cve_source_sync['ecosystems'] = input_json.get('cve_ecosystem', [])
        _session.post(url, json=cve_source_sync)
        resp['message'] = resp['message'] + " for cve source update"

    logger.info("Sync operation called.. Message->", resp['message'])
    return flask.jsonify(resp), 200


@app.route('/api/v1/register', methods=['POST'])
@login_required
def register():
    """
    Endpoint for registering a new repository.

    Registers new information and
    updates existing repo information.
    """
    resp_dict = {
        "success": True,
        "summary": ""
    }
    input_json = request.get_json()
    if request.content_type != 'application/json':
        resp_dict["success"] = False
        resp_dict["summary"] = "Set content type to application/json"
        return flask.jsonify(resp_dict), 400

    validated_data = validate_request_data(input_json)
    if not validated_data[0]:
        resp_dict["success"] = False
        resp_dict["summary"] = validated_data[1]
        return flask.jsonify(resp_dict), 404

    try:
        repo_info = DatabaseIngestion.get_info(input_json.get('git-url'))
        if repo_info.get('is_valid'):
            data = repo_info.get('data')
            # Update the record to reflect new git_sha if any.
            DatabaseIngestion.update_data(input_json)
        else:
            try:
                # First time ingestion
                DatabaseIngestion.store_record(input_json)
                status = scan_repo(input_json)
                if status is not True:
                    resp_dict["success"] = False
                    resp_dict["summary"] = "New Repo Scan Initialization Failure"
                    return flask.jsonify(resp_dict), 500

                resp_dict["summary"] = "Repository {} with commit-hash {} " \
                                       "has been successfully registered. " \
                                       "Please check back for report after some time." \
                    .format(input_json.get('git-url'),
                            input_json.get('git-sha'))

                return flask.jsonify(resp_dict), 200
            except Exception as e:
                resp_dict["success"] = False
                resp_dict["summary"] = "Database Ingestion Failure due to: {}" \
                    .format(e)
                return flask.jsonify(resp_dict), 500
    except Exception as e:
        resp_dict["success"] = False
        resp_dict["summary"] = "Cannot get information about repository {} " \
                               "due to {}" \
            .format(input_json.get('git-url'), e)
        return flask.jsonify(resp_dict), 500

    # Scan the repository irrespective of report is available or not.
    status = scan_repo(input_json)
    if status is not True:
        resp_dict["success"] = False
        resp_dict["summary"] = "New Repo Scan Initialization Failure"
        return flask.jsonify(resp_dict), 500

    resp_dict.update({
        "summary": "Repository {} was already registered, but no report for "
                   "commit-hash {} was found. Please check back later."
                   .format(input_json.get('git-url'), input_json.get('git-sha')),
        "last_scanned_at": data['last_scanned_at'],
        "last_scan_report": None
    })

    return flask.jsonify(resp_dict), 200


@app.route('/api/v1/report')
@login_required
def report():
    """Endpoint for fetching generated scan report."""
    repo = request.args.get('git-url')
    sha = request.args.get('git-sha')
    response = dict()
    result = retrieve_worker_result(sha, "ReportGenerationTask")
    if result:
        task_result = result.get('task_result')
        if task_result:
            response.update({
                "git_url": repo,
                "git_sha": sha,
                "scanned_at": task_result.get("scanned_at"),
                "dependencies": task_result.get("dependencies")
            })

            if task_result.get('lock_file_absent'):
                response.update({
                    "lock_file_absent": task_result.get("lock_file_absent"),
                    "message": task_result.get("message")
                })
                return flask.jsonify(response), 400

            return flask.jsonify(response), 200
        else:
            response.update({
                "status": "failure",
                "message": "Failed to retrieve scan report"
            })
            return flask.jsonify(response), 500
    else:
        response.update({
            "status": "failure",
            "message": "No report found for this repository"
        })
        return flask.jsonify(response), 404


@app.route('/api/v1/user-repo/scan', methods=['POST'])
@login_required
def user_repo_scan():
    """Experimental endpoint."""
    # TODO: please refactor this method is it would be possible to test it properly
    # json data and files cannot be a part of same request. Hence, we need to use form data here.
    validate_string = "{} cannot be empty"
    resp_dict = {
        "status": "success",
        "summary": ""
    }
    git_url = request.headers.get("git-url")

    if not git_url:
        validate_string = validate_string.format("git-url")
        resp_dict["status"] = 'failure'
        resp_dict["summary"] = validate_string
        return flask.jsonify(resp_dict), 400

    req_json = request.json
    set_direct = set()
    set_transitive = set()
    if req_json is None:
        validate_string = validate_string.format("input json")
        resp_dict["status"] = 'failure'
        resp_dict["summary"] = validate_string
        return flask.jsonify(resp_dict), 400

    result_ = req_json.get("result", None)
    if result_ is None:
        validate_string = validate_string.format("Result dictionary")
        resp_dict["status"] = 'failure'
        resp_dict["summary"] = validate_string
        return flask.jsonify(resp_dict), 400

    for res_ in result_:
        details_ = res_.get("details", None)
        set_direct, set_transitive = DataExtractor.get_details_from_results(details_)

    dependencies = {
        'direct': list(set_direct),
        'transitive': list(set_transitive)
    }

    try:
        repo_cves = RepoDependencyCreator.create_repo_node_and_get_cve(
            github_repo=git_url, deps_list=dependencies)

        # We get a list of reports here since the functionality is meant to be
        # re-used for '/notify' call as well.
        repo_reports = RepoDependencyCreator.generate_report(repo_cves=repo_cves,
                                                             deps_list=dependencies)
        for repo_report in repo_reports:
            notification = UserNotification.generate_notification(report=repo_report)
            UserNotification.send_notification(notification=notification,
                                               token=SERVICE_TOKEN)
    except Exception as ex:
        return flask.jsonify({
            "error": ex.__str__()
        }), 500

    resp_dict.update({
        "summary": "Report for {} is being generated in the background. You will "
                   "be notified via your preferred openshift.io notification mechanism "
                   "on its completion.".format(git_url)
    })

    return flask.jsonify(resp_dict), 200


@app.route('/api/v1/user-repo/scan/experimental', methods=['POST'])
@login_required
def user_repo_scan_experimental():  # pragma: no cover
    """
    Endpoint for scanning an OSIO user's repository.

    Runs a scan to find out security vulnerability in a user's repository
    """
    resp_dict = {
        "status": "success",
        "summary": ""
    }

    if request.content_type != 'application/json':
        resp_dict["status"] = "failure"
        resp_dict["summary"] = "Set content type to application/json"
        return flask.jsonify(resp_dict), 400

    input_json = request.get_json()

    validate_string = "{} cannot be empty"
    if 'git-url' not in input_json:
        validate_string = validate_string.format("git-url")
        resp_dict["status"] = 'failure'
        resp_dict["summary"] = validate_string
        return flask.jsonify(resp_dict), 400

    url = input_json['git-url'].replace('git@github.com:', 'https://github.com/')
    input_json['git-url'] = url

    # Call the worker flow to run a user repository scan asynchronously
    status = alert_user(input_json, SERVICE_TOKEN)
    if status is not True:
        resp_dict["status"] = "failure"
        resp_dict["summary"] = "Scan initialization failure"
        return flask.jsonify(resp_dict), 500

    resp_dict.update({
        "summary": "Report for {} is being generated in the background. You will "
                   "be notified via your preferred openshift.io notification mechanism "
                   "on its completion.".format(input_json.get('git-url')),
    })

    return flask.jsonify(resp_dict), 200


@app.route('/api/v1/user-repo/notify', methods=['POST'])
@login_required
def notify_user():
    """
    Endpoint for notifying security vulnerability in a repository.

    Runs a scan to find out security vulnerability in a user's repository
    """
    resp_dict = {
        "status": "success",
        "summary": ""
    }

    if request.content_type != 'application/json':
        resp_dict["status"] = "failure"
        resp_dict["summary"] = "Set content type to application/json"
        return flask.jsonify(resp_dict), 400

    input_json = request.get_json()

    validate_string = "{} cannot be empty"
    if 'epv_list' not in input_json:
        resp_dict["status"] = "failure"
        resp_dict["summary"] = validate_string.format('epv_list')
        return flask.jsonify(resp_dict), 400

    # Call the worker flow to run a user repository scan asynchronously
    status = alert_user(input_json, SERVICE_TOKEN, epv_list=input_json['epv_list'])
    if status is not True:
        resp_dict["status"] = "failure"
        resp_dict["summary"] = "Scan initialization failure"
        return flask.jsonify(resp_dict), 500

    resp_dict.update({
        "summary": "Report for {} is being generated in the background. You will "
                   "be notified via your preferred openshift.io notification mechanism "
                   "on its completion.".format(input_json.get('git-url')),
    })

    return flask.jsonify(resp_dict), 200


@app.route('/api/v1/user-repo/drop', methods=['POST'])
@login_required
def drop():  # pragma: no cover
    """
    Endpoint to stop monitoring OSIO users' repository.

    Runs a scan to find out security vulnerability in a user's repository
    """
    resp_dict = {
        "status": "success",
        "summary": ""
    }

    if request.content_type != 'application/json':
        resp_dict["status"] = "failure"
        resp_dict["summary"] = "Set content type to application/json"
        return flask.jsonify(resp_dict), 400

    input_json = request.get_json()

    validate_string = "{} cannot be empty"

    if 'git-url' not in input_json:
        resp_dict["status"] = "failure"
        resp_dict["summary"] = validate_string.format('git-url')
        return flask.jsonify(resp_dict), 400

    gremlin_query = "g.V().has('repo_url', '{git_url}').outE().drop().iterate()" \
                    .format(git_url=input_json.get('git-url'))
    payload = {
        "gremlin": gremlin_query
    }

    raw_response = requests.post(url=GREMLIN_SERVER_URL_REST, json=payload)

    if raw_response.status_code != 200:
        # This raises an HTTPError which will be handled by `handle_error()`.
        raw_response.raise_for_status()

    resp_dict['summary'] = 'Repository scan unsubscribed'
    return flask.jsonify(resp_dict), 200


@app.route('/api/v1/stacks-report/list/<frequency>', methods=['GET'])
def list_stacks_reports(frequency='weekly'):
    """
    Endpoint to fetch the list of generated stacks reports.

    The list is fetched based on the frequency which is either weekly or monthly.
    """
    return flask.jsonify(_s3_helper.list_objects(frequency))


@app.route('/api/v1/stacks-report/report/<path:report>', methods=['GET'])
def get_stacks_report(report):
    """
    Endpoint to retrieve a generated stacks report.

    A report matching with the filename retrieved using the /stacks-report/list/{frequency}
    will be returned.
    """
    return flask.jsonify(_s3_helper.get_object_content(report))


@app.route('/api/v1/ingestion-report/list', methods=['GET'])
def list_ingestion_reports():
    """Endpoint to fetch the list of generated ingestion reports."""
    return flask.jsonify(_s3_helper.list_objects("ingestion-data/epv"))


@app.route('/api/v1/ingestion-report/report/<path:report>', methods=['GET'])
def get_ingestion_report(report):
    """
    Endpoint to retrieve a generated ingestion report.

    A report matching with the filename retrieved using the ingestion-report/list
    will be returned.
    """
    return flask.jsonify(_s3_helper.get_object_content(report))


@app.route('/api/v1/sentry-report/list', methods=['GET'])
def list_sentry_reports():
    """Endpoint to fetch the list of generated sentry reports."""
    return flask.jsonify(_s3_helper.list_objects("sentry-error-data"))


@app.route('/api/v1/sentry-report/report/<path:report>', methods=['GET'])
def get_sentry_report(report):
    """
    Endpoint to retrieve a generated sentry report.

    A report matching with the filename retrieved using the sentry-report/list
    will be returned.
    """
    return flask.jsonify(_s3_helper.get_object_content(report))


@app.route('/api/v1/stacks-report/compare', methods=['GET'])
def compare_stacks_report():
    """
    Endpoint to compare generated stacks reports for past days.

    Maximum number of days 7.
    """
    comparison_days = int(request.args.get('days'))
    if comparison_days < 2 and comparison_days > 7:
        # Return bad request
        return flask.jsonify(error='Invalid number of days provided to compare reports.'
                                   'Range is 2-7'), 400

    return flask.jsonify(generate_comparison(comparison_days))


@app.errorhandler(HTTPError)
def handle_error(e):  # pragma: no cover
    """Handle http error response."""
    return flask.jsonify({
        "error": e.error
    }), e.status_code


@app.errorhandler(AuthError)
def api_401_handler(err):
    """Handle AuthError exceptions."""
    return flask.jsonify(error=err.error), err.status_code


if __name__ == "__main__":  # pragma: no cover
    app.run()
