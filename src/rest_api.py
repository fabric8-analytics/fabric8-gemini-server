"""Definition of the routes for gemini server."""
import flask
from flask import Flask, request
from flask_cors import CORS
from utils import DatabaseIngestion, scan_repo, validate_request_data,\
    retrieve_worker_result, alert_user
from f8a_worker.setup_celery import init_selinon
from auth import login_required
from exceptions import HTTPError

app = Flask(__name__)
CORS(app)

init_selinon()


@app.route('/api/v1/readiness')
def readiness():
    """Readiness probe."""
    return flask.jsonify({}), 200


@app.route('/api/v1/liveness')
def liveness():
    """Liveness probe."""
    return flask.jsonify({}), 200


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
            return flask.jsonify(response), 200
        else:
            response.update({
                "status": "failure",
                "message": "Failed to retrieve scan report"
            })
            return flask.jsonify(response), 404
    else:
        response.update({
            "status": "failure",
            "message": "No report found for this repository"
        })
        return flask.jsonify(response), 404


@app.route('/api/v1/user-repo/scan', methods=['POST'])
@login_required
def user_repo_scan():
    """
    Endpoint for scanning an OSIO user's repository.

    Runs a scan to find out security vulnerability in a user's repository
    """
    resp_dict = {
        "status": "success",
        "summary": ""
    }

    # Request validation section
    input_json = request.get_json()

    # Return a dummy response for the endpoint while the development is in progress
    if not 'dev' in input_json:
        return flask.jsonify({'summary': 'Repository scan initiated'}), 200

    if request.content_type != 'application/json':
        resp_dict["success"] = False
        resp_dict["summary"] = "Set content type to application/json"
        return flask.jsonify(resp_dict), 400

    validate_string = "{} cannot be empty"
    if 'git-url' not in input_json:
        validate_string = validate_string.format("git-url")
        return False, validate_string

    # Call the worker flow to run a user repository scan asynchronously
    status = alert_user(input_json)
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
    # Request validation section
    input_json = request.get_json()

    # Return a dummy response for the endpoint while the development is in progress
    if not 'dev' in input_json:
        return flask.jsonify({'summary': 'Notification service called'}), 200

    resp_dict = {}
    if request.content_type != 'application/json':
        resp_dict["success"] = False
        resp_dict["summary"] = "Set content type to application/json"
        return flask.jsonify(resp_dict), 400

    validate_string = "{} cannot be empty"
    if 'vulnerable-components' not in input_json:
        validate_string = validate_string.format("vulnerable-components")
        return False, validate_string

    # Call the worker flow to run a user repository scan asynchronously
    status = alert_user(input_json, skip_dep_tree=True)
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
def drop():
    """
    Endpoint for scanning an OSIO user's repository.

    Runs a scan to find out security vulnerability in a user's repository
    """
    # Request validation section
    input_json = request.get_json()

    # Return a dummy response for the endpoint while the development is in progress
    if not 'dev' in input_json:
        return flask.jsonify({'summary': 'Repository scan unsubscribed'}), 200



@app.errorhandler(HTTPError)
def handle_error(e):  # pragma: no cover
    """Handle http error response."""
    return flask.jsonify({
        "error": e.error
    }), e.status_code


if __name__ == "__main__":  # pragma: no cover
    app.run()
