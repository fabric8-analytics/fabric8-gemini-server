"""Definition of the routes for gemini server."""
import flask
from flask import Flask, request, current_app
from flask_cors import CORS
from utils import DatabaseIngestion, scan_repo, validate_request_data, retrieve_worker_result
from f8a_worker.setup_celery import init_selinon

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


@app.route('/api/v1/scan', methods=['POST'])
def scan():
    """Scan endpoint for consumption of the scheduled job."""
    input_json = request.get_json()
    git_url = input_json.get('git_url')
    r = {"success": True, "summary": ""}
    if git_url:
        try:
            repo_info = DatabaseIngestion.get_info(git_url)
            if repo_info.get('is_valid'):
                data = repo_info.get('data')
                git_sha = data['git_sha']
                email_ids = data['email_ids']
                scan_repo({
                    "git_url": git_url,
                    "git_sha": git_sha,
                    "email_ids": email_ids
                })
                r["summary"] = "Repository with git_url {} and git_sha {} has been" \
                               "successfully scheduled for scanning."\
                    .format(git_url, git_sha)
                return flask.jsonify(r), 200
            else:
                r["success"] = False
                r["summary"] = repo_info.get("error")
                return flask.jsonify(r), 500
        except Exception as e:
            r["success"] = False
            r["summary"] = str(e)
            return flask.jsonify(r), 500
    else:
        # TODO: Do scan for all repos if git_url is not present
        r["summary"] = "Please provide git_url to scan."
        r["success"] = False
        return flask.jsonify(r), 500


@app.route('/api/v1/register', methods=['POST'])
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
            git_sha = data["git_sha"]
            # Update the record to reflect new git_sha if any.
            DatabaseIngestion.update_data(input_json)
        else:
            try:
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
    except Exception:
        resp_dict["success"] = False
        resp_dict["summary"] = "Cannot get information about repository {}" \
            .format(input_json.get('git-url'))
        return flask.jsonify(resp_dict), 500

    # Checks if data is defined and compares new git_sha with old.
    is_new_commit_hash = input_json.get("git-sha") != data["git_sha"]

    worker_result = retrieve_worker_result(git_sha, "ReportGenerationTask")
    if worker_result:
        resp_dict["summary"] = "Repository {} with commit-hash {} " \
                               "has already been registered and scanned. " \
                               "Please check the scan report for details. " \
            .format(input_json.get('git-url'),
                    input_json.get('git-sha'))

        if is_new_commit_hash:
            resp_dict["summary"] = "Repository {} with commit-hash {} " \
                                   "has already been registered and scanned. " \
                                   "Please check the scan report for details. " \
                                   "You can check the report for commit-hash {} after" \
                                   "some time." \
                .format(input_json.get('git-url'),
                        data["git_sha"], input_json.get("git-sha"))

        task_result = worker_result.get('task_result')
        if task_result:
            resp_dict.update({
                "last_scanned_at": task_result.get('scanned_at'),
                "last_scan_report": task_result.get('dependencies')
            })
            return flask.jsonify(resp_dict), 200
        else:
            resp_dict["success"] = False
            resp_dict["summary"] = "Failed to retrieve scan report."
            return flask.jsonify(resp_dict), 500

    resp_dict.update({
        "summary": "Repository {} was already registered, but no report for "
                   "commit-hash {} was found. Please check back later."
                   .format(input_json.get('git-url'), git_sha),
        "last_scanned_at": data['last_scanned_at'],
        "last_scan_report": None
    })

    return flask.jsonify(resp_dict), 200


@app.route('/api/v1/report/<repo>')
def report(repo):
    """Endpoint for fetching generated scan report."""
    return flask.jsonify({})


if __name__ == "__main__":
    app.run()
