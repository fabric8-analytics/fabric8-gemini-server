"""Test module."""

from flask import current_app, url_for
import requests
import os
import pytest

payload = {
}
port = os.getenv("GEMINI_API_SERVICE_PORT", "5000")

url = "http://localhost:{port}/api/v1".format(port=port)


def api_route_for(route):
    """Construct an URL to the endpoint for given route."""
    return '/api/v1/' + route


def get_json_from_response(response):
    """Decode JSON from response."""
    return json.loads(response.data.decode('utf8'))


def test_readiness_endpoint(client):
    """Test the heart beat endpoint."""
    response = client.get(api_route_for("readiness"))
    assert response.status_code == 200
    json_data = get_json_from_response(response)
    # assert "status" in json_data
    # assert json_data["status"] == "ok"
