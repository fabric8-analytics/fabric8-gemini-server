"""Test module."""

from flask import current_app, url_for
import requests
import os
import pytest
import json

payload = {
    "email_ids": "abcd@gmail.com",
    "git_sha": "somesha",
    "git_url": "test",
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


def test_register_api_endpoint(client):
    """Test function for register endpoint."""
    reg_resp = client.post(api_route_for("register"), data=json.dumps(payload))
    assert reg_resp.status_code == 200
    jsn = get_json_from_response(reg_resp)
    assert(jsn["success"] == true)
    assert(jsn['data']["git_sha"] == payload["git_sha"])
    assert(jsn['data']["git_url"] == payload["git_url"])
    assert(jsn['data']["email_ids"] == payload["email_ids"])
