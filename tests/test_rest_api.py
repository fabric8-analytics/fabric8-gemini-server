"""Test module."""

import json
from unittest.mock import patch
from utils import DatabaseIngestion

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
    assert response.status_code == 404
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


# def test_scan_endpoint(client):
#     """Test the /api/v1/user-repo/scan endpoint."""
#     reg_resp = client.post(api_route_for('user-repo/scan'),
#                            data=json.dumps(payload_user_repo_scan_drop),
#                            content_type='application/json')
#     assert reg_resp.status_code == 200
#
#
# def test_drop_endpoint(client):
#     """Test the /api/v1/user-repo/drop endpoint."""
#     reg_resp = client.post(api_route_for('user-repo/scan'),
#                            data=json.dumps(payload_user_repo_scan_drop),
#                            content_type='application/json')
#     assert reg_resp.status_code == 200
#
#
# def test_notify_endpoint(client):
#     """Test the /api/v1/user-repo/notify endpoint."""
#     reg_resp = client.post(api_route_for('user-repo/scan'),
#                            data=json.dumps(payload_user_repo_notify),
#                            content_type='application/json')
#     assert reg_resp.status_code == 200
