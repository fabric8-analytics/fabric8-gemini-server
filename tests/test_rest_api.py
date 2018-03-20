"""Test module."""

from flask import current_app, url_for
from f8a_worker.models import OSIORegisteredRepos
from sqlalchemy import create_engine
from f8a_worker.models import Base
from pytest_mock import mocker

import requests
import os
import pytest
import json

payload = {
    "email_ids": "abcd@gmail.com",
    "git_sha": "somesha",
    "git_url": "test"
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


def test_register_api_endpoint(client, mocker):
    """Test function for register endpoint."""
    create_database()
    scan_mock = mocker.patch("src.rest_api.scan_repo")
    scan_mock.return_value = True
    reg_resp = client.post(api_route_for("register"),
                           data=json.dumps(payload), content_type='application/json')
    assert reg_resp.status_code == 200
    jsn = get_json_from_response(reg_resp)
    assert(jsn["success"])
    assert(jsn['data']["data"]["git_sha"] == payload["git_sha"])
    assert(jsn['data']["data"]["git_url"] == payload["git_url"])
    assert(jsn['data']["data"]["email_ids"] == payload["email_ids"])


def create_database():
    """Help method to create database."""
    con_string = 'postgresql://{user}:{passwd}@{pg_host}:' + \
                 '{pg_port}/{db}?sslmode=disable'
    connection = con_string.format(
        user=os.getenv('POSTGRESQL_USER'),
        passwd=os.getenv('POSTGRESQL_PASSWORD'),
        pg_host=os.getenv(
            'PGBOUNCER_SERVICE_HOST',
            'bayesian-pgbouncer'),
        pg_port=os.getenv(
            'PGBOUNCER_SERVICE_PORT',
            '5432'),
        db=os.getenv('POSTGRESQL_DATABASE'))
    engine = create_engine(connection)
    Base.metadata.drop_all(engine)
    OSIORegisteredRepos.__table__.create(engine)
