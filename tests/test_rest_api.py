"""Test module."""

import json

payload = {
    "email-ids": "abcd@gmail.com",
    "git-sha": "somesha",
    "git-url": "test"
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


def test_report_endpoint(client, mocker):
    """Test the /api/v1/report endpoint."""
    retrieve_worker_result_mock = mocker.patch("src.rest_api.retrieve_worker_result")
    retrieve_worker_result_mock.return_value = False
    response = client.get(api_route_for('report?git-url=test&git-sha=test'))
    assert response.status_code == 404
    json_data = get_json_from_response(response)
    assert json_data == {
        "status": "failure",
        "message": "No report found for this repository"
    }
    retrieve_worker_result_mock.return_value = {
        "task_result": None
    }
    response = client.get(api_route_for('report?git-url=test&git-sha=test'))
    assert response.status_code == 404
    json_data = get_json_from_response(response)
    assert json_data == {
        "status": "failure",
        "message": "Failed to retrieve scan report"
    }
    retrieve_worker_result_mock.return_value = {
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


def test_register_endpoint(client):
    """Test the /api/v1/register endpoint."""
    pass
