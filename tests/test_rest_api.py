"""Test module."""

import json
from unittest.mock import patch
from utils import DatabaseIngestion
from pathlib import Path
from parsers.maven_parser import MavenParser
from src.repo_dependency_creator import RepoDependencyCreator
from src.notification.user_notification import UserNotification
from utils import GREMLIN_SERVER_URL_REST
import os

payload = {
    "email-ids": "abcd@gmail.com",
    "git-sha": "somesha",
    "git-url": "test"
}

payload_1 = {
    "git-sha": "sha"
}

payload_user_repo_scan_drop = {
    "git-url": "test",
    "email-ids": ["abcd@gmail.com"]
}

payload_user_repo_notify = {
    "epv_list": [
        {
            "ecosystem": "maven",
            "name": "io.vertx:vertx-core",
            "version": "3.5.2"
        }
    ]
}

payload_user_repo_scan = {
    "ecosystem": "maven",
    "git-sha": "somesha",
    "git-url": "test",
    "dependencyFile[]": [(str(Path(__file__).parent / 'files/direct-dependencies.txt'),
                          'direct-dependencies.txt'),
                         (str(Path(__file__).parent / 'files/transitive-dependencies.txt'),
                          'transitive-dependencies.txt')]
}


def get_payload_json():
    """Help function to read sample payload."""
    dir_path = os.path.dirname(os.path.realpath(__file__))

    with open(str(dir_path) + '/files/scan-test-data.json') as f:
        data = json.load(f)

    return data


payload_scan_data = get_payload_json()


def mocked_requests_post(url, **kwargs):
    """Mock function for requests.post."""
    class MockResponse:
        def __init__(self, data, json, status_code, **kwargs):
            self.data = data
            self.json_data = json
            self.status_code = status_code
            self.kwargs = kwargs

        def json(self):
            return self.json_data

    if url == GREMLIN_SERVER_URL_REST:
        return MockResponse(data='{}', json={}, status_code=200, kwargs=kwargs)
    elif url == '/api/notify':
        return MockResponse(data='{}', json={}, status_code=202, kwargs=kwargs)

    return MockResponse(data='{}', json={}, status_code=200, kwargs=kwargs)


def mocked_generate_report(repo_cves, deps_list):
    """Mock generate report."""
    return [{
        "result": [repo_cves, deps_list]
    }]


def mocked_generate_notification(report):
    """Mock generate notification."""
    result = {
        "data": {
            "attributes": {
                "custom": report,
                "id": report.get('repo_url', ""),
                "type": "analytics.notify.cve"
            },
            "id": "test",
            "type": "notifications"
        }
    }
    return result


def api_route_for(route):
    """Construct an URL to the endpoint for given route."""
    return '/api/v1/' + route


def get_json_from_response(response):
    """Decode JSON from response."""
    return json.loads(response.data.decode('utf8'))


def test_readiness_endpoint(client):
    """Test the /api/v1/readiness endpoint."""
    response = client.get(api_route_for("readiness"))
    assert response.status_code == 200
    json_data = get_json_from_response(response)
    assert json_data == {}, "Empty JSON response expected"


def test_liveness_endpoint(client):
    """Test the /api/v1/liveness endpoint."""
    response = client.get(api_route_for("liveness"))
    assert response.status_code == 200
    json_data = get_json_from_response(response)
    assert json_data == {}


@patch("src.rest_api.retrieve_worker_result")
def test_report_endpoint(mocker, client):
    """Test the /api/v1/report endpoint."""
    mocker.return_value = False
    response = client.get(api_route_for('report?git-url=test&git-sha=test'))
    assert response.status_code == 404
    json_data = get_json_from_response(response)
    assert json_data == {
        "status": "failure",
        "message": "No report found for this repository"
    }
    mocker.return_value = {
        "task_result": None
    }
    response = client.get(api_route_for('report?git-url=test&git-sha=test'))
    assert response.status_code == 500
    json_data = get_json_from_response(response)
    assert json_data == {
        "status": "failure",
        "message": "Failed to retrieve scan report"
    }
    mocker.return_value = {
        "task_result": {
            "scanned_at": "1",
            "dependencies": []
        }
    }
    response = client.get(api_route_for('report?git-url=test&git-sha=test'))
    assert response.status_code == 200
    json_data = get_json_from_response(response)
    assert json_data == {
        "git_url": "test",
        "git_sha": "test",
        "scanned_at": "1",
        "dependencies": []
    }
    mocker.return_value = {
        "task_result": {
            "scanned_at": "1",
            "dependencies": [],
            "lock_file_absent": True,
            "message": "test"
        }
    }
    response = client.get(api_route_for('report?git-url=test&git-sha=test'))
    assert response.status_code == 400
    json_data = get_json_from_response(response)
    assert json_data == {
        "git_url": "test",
        "git_sha": "test",
        "scanned_at": "1",
        "dependencies": [],
        "lock_file_absent": True,
        "message": "test"
    }


def test_register_endpoint_1(client):
    """Test the /api/v1/register endpoint."""
    reg_resp = client.post(api_route_for('register'),
                           data=json.dumps(payload))
    assert reg_resp.status_code == 400
    reg_resp_json = get_json_from_response(reg_resp)
    assert reg_resp_json == {
        "success": False,
        "summary": "Set content type to application/json"
    }


def test_register_endpoint_2(client):
    """Test the /api/v1/register endpoint."""
    reg_resp = client.post(api_route_for('register'),
                           data=json.dumps(payload_1),
                           content_type='application/json')
    assert reg_resp.status_code == 404


@patch.object(DatabaseIngestion, "get_info")
@patch.object(DatabaseIngestion, "update_data")
@patch("src.rest_api.scan_repo")
def test_register_endpoint_3(scan_repo, update_data, get_info, client):
    """Test the /api/v1/register endpoint."""
    get_info.return_value = {
        "is_valid": True,
        "data": {
            "last_scanned_at": "1"
        }
    }
    update_data.return_value = True
    scan_repo.return_value = True
    reg_resp = client.post(api_route_for('register'),
                           data=json.dumps(payload),
                           content_type='application/json')
    assert reg_resp.status_code == 200
    scan_repo.return_value = False
    reg_resp = client.post(api_route_for('register'),
                           data=json.dumps(payload),
                           content_type='application/json')
    assert reg_resp.status_code == 500


@patch.object(DatabaseIngestion, "get_info")
@patch.object(DatabaseIngestion, "store_record")
@patch("src.rest_api.scan_repo")
def test_register_endpoint_4(scan_repo, store_record, get_info, client):
    """Test the /api/v1/register endpoint."""
    get_info.return_value = {
        "is_valid": False
    }
    store_record.return_value = True
    scan_repo.return_value = True
    reg_resp = client.post(api_route_for('register'),
                           data=json.dumps(payload),
                           content_type='application/json')
    assert reg_resp.status_code == 200
    scan_repo.return_value = False
    reg_resp = client.post(api_route_for('register'),
                           data=json.dumps(payload),
                           content_type='application/json')
    assert reg_resp.status_code == 500


def test_register_endpoint_5(client):
    """Test the /api/v1/register endpoint."""
    reg_resp = client.post(api_route_for('register'),
                           data=json.dumps(payload),
                           content_type='application/json')
    assert reg_resp.status_code == 500


@patch.object(DatabaseIngestion, "get_info")
def test_register_endpoint_6(get_info, client):
    """Test the /api/v1/register endpoint."""
    get_info.return_value = {
        "is_valid": False
    }
    reg_resp = client.post(api_route_for('register'),
                           data=json.dumps(payload),
                           content_type='application/json')
    assert reg_resp.status_code == 500


def test_user_repo_scan_endpoint(client):
    """Test the /api/v1/user-repo/scan endpoint."""
    resp = client.post(api_route_for('user-repo/scan'),
                       headers={'git-url': 'test'},
                       data=payload)

    assert resp.status_code == 400
    json_data = get_json_from_response(resp)
    assert json_data == {
        "status": "failure",
        "summary": "input json cannot be empty"
    }


def test_user_repo_scan_endpoint_1(client):
    """Test the /api/v1/user-repo/scan endpoint."""
    resp = client.post(api_route_for('user-repo/scan'),
                       data=json.dumps(payload_scan_data),
                       content_type='application/json')
    assert resp.status_code == 400
    json_data = get_json_from_response(resp)
    assert json_data == {
        "status": "failure",
        "summary": "git-url cannot be empty"
    }


@patch.object(MavenParser, "parse_output_files")
@patch.object(RepoDependencyCreator, "create_repo_node_and_get_cve")
@patch("src.rest_api.RepoDependencyCreator.generate_report",
       side_effect=mocked_generate_report)
@patch("src.rest_api.UserNotification.generate_notification",
       side_effect=mocked_generate_notification)
@patch.object(UserNotification, "send_notification")
@patch("src.repo_dependency_creator.requests.post",
       side_effect=mocked_requests_post)
@patch("src.notification.user_notification.requests.post",
       side_effect=mocked_requests_post)
def test_user_repo_scan_endpoint_2(_r_post, _u_post, send_notification, generate_notification,
                                   _generate_report, create_repo_node_and_get_cve,
                                   parse_output_file, client):
    """Test the /api/v1/user-repo/scan endpoint."""
    parse_output_file.return_value = set(), set()
    create_repo_node_and_get_cve.return_value = {'result': {
        "data": []
    }}
    generate_notification.return_value = {'notification-payload': 'notification'}
    send_notification.return_value = {'status': 'success'}
    resp = client.post(api_route_for('user-repo/scan'),
                       headers={'git-url': 'test'},
                       data=json.dumps(payload_scan_data),
                       content_type='application/json')

    assert resp.status_code == 200


def test_notify_user_endpoint(client):
    """Test the /api/v1/user-repo/notify endpoint."""
    resp = client.post(api_route_for('user-repo/notify'),
                       data=json.dumps(payload))

    assert resp.status_code == 400


def test_notify_user_endpoint_1(client):
    """Test the /api/v1/user-repo/notify endpoint."""
    resp = client.post(api_route_for('user-repo/notify'),
                       data=json.dumps(payload),
                       content_type='application/json')

    assert resp.status_code == 400


@patch('src.rest_api.alert_user')
def test_notify_user_endpoint_2(alert_user, client):
    """Test the /api/v1/user-repo/notify endpoint."""
    alert_user.return_value = False
    resp = client.post(api_route_for('user-repo/notify'),
                       data=json.dumps(payload_user_repo_notify),
                       content_type='application/json')

    assert resp.status_code == 500

    alert_user.return_value = True

    resp = client.post(api_route_for('user-repo/notify'),
                       data=json.dumps(payload_user_repo_notify),
                       content_type='application/json')

    assert resp.status_code == 200
