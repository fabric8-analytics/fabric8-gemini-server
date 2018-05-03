"""Test module."""

from flask import current_app, url_for
from f8a_worker.models import OSIORegisteredRepos
from sqlalchemy import create_engine
from f8a_worker.models import Base
from pytest_mock import mocker
from tests.conftest import create_database

import requests
import os
import pytest
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


def test_report_endpoint(client):
    """Test the /api/v1/report endpoint."""
    response = client.get(api_route_for("report"))
    assert response.status_code == 401
    json_data = get_json_from_response(response)
    assert "error" in json_data
    assert json_data["error"] == "Authentication failed - could not decode JWT token"


def test_register_endpoint(client):
    """Test the /api/v1/register endpoint."""
    pass
