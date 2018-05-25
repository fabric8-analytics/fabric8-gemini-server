"""Definition of the routes for gemini server."""
import flask
from flask import Flask, request
from flask_cors import CORS
from utils import DatabaseIngestion, scan_repo, validate_request_data, retrieve_worker_result
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


@app.errorhandler(HTTPError)
def handle_error(e):
    """Handle http error response."""
    return flask.jsonify({
        "error": e.error
    }), e.status_code


if __name__ == "__main__":
    app.run()
