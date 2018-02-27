"""Definition of the routes for gemini server."""
import flask
from flask import Flask, request
from flask_cors import CORS

from utils import persist_repo_in_db, scan_repo

app = Flask(__name__)
CORS(app)


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
    r = {}
    return flask.jsonify({}), 200


@app.route('/api/v1/register', methods=['POST'])
def register():
    """Endpoint for registering a new repository or to update existing repo information."""
    input_json = request.get_json()
    if 'github_repo' not in input_json:
        return flask.jsonify({'error': '"github_repo" is a required parameter'}), 400

    if 'github_sha' not in input_json:
        return flask.jsonify({'error': '"github_sha" is a required parameter'}), 400

    if 'email_ids' not in input_json:
        return flask.jsonify({'error': '"email_ids" is a required parameter'}), 400

    status = persist_repo_in_db(input_json)
    if status is not True:
        return flask.jsonify({'error': 'New repo registration failed as {}'.
                             format(status.get('message', 'undefined'))}), 500

    status = scan_repo(input_json)
    if status is not True:
        return flask.jsonify({'error': 'New repo scan initialization failed as {}'.
                             format(status.get('message', 'undefined'))}), 500

    msg = '{} successfully registered'.format(input_json['github_repo'])
    return flask.jsonify({'message': msg}), 200


@app.route('/api/v1/report/<repo>')
def report(repo):
    """Endpoint for fetching generated scan report."""
    return flask.jsonify({})


if __name__ == "__main__":
    app.run()
