"""Test module for classes and functions found in the utils module."""
from rest_api import app

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm.exc import NoResultFound

from src.utils import (
    DatabaseIngestion, alert_user, fetch_public_key, get_session, get_session_retry,
    retrieve_worker_result, scan_repo, server_run_flow, validate_request_data,
    fix_gremlin_output, generate_comparison, get_first_query_result, get_parser_from_ecosystem,
    PostgresPassThrough, GraphPassThrough
)

from src.parsers.maven_parser import MavenParser
from src.parsers.node_parser import NodeParser

from unittest.mock import patch
import requests
import pytest
import os
import json

ppt = PostgresPassThrough()
gpt = GraphPassThrough()

mocked_object_response = {'stacks_summary': {'total_average_response_time': '200ms'}}


class MockResponse:
    """Mocks the requests.get call."""

    def __init__(self, json_data, status_code, text):
        """Initialize the object."""
        self.json_data = json_data
        self.status_code = status_code
        self.text = text

    def json(self):
        """Return json representation of data."""
        return self.json_data


def test_validate_request_data():
    """Test the function validate_request_data."""
    valid, result = validate_request_data({})
    assert not valid
    assert result == "git-url cannot be empty"

    valid, result = validate_request_data({"git-url": "something"})
    assert not valid
    assert result == "git-sha cannot be empty"

    valid, result = validate_request_data({"git-url": "something",
                                           "git-sha": "something"})
    assert valid
    assert not result

    valid, result = validate_request_data({"git-url": "something",
                                           "git-sha": "something",
                                           "email-ids": "something"})
    assert valid
    assert not result


def test_get_session():
    """Test the function get_session."""
    session = get_session()
    assert session is not None


@patch("src.utils.query_worker_result", side_effect=SQLAlchemyError())
def test_retrieve_worker_result(_query):
    """Test the function retrieve_worker_result."""
    with pytest.raises(SQLAlchemyError):
        retrieve_worker_result("test", "test")


@patch("src.utils.query_worker_result", return_value=None)
@patch("src.utils.get_first_query_result", return_value=None)
def test_retrieve_worker_result_1(_a, _b):
    """Test the function retrieve_worker_result."""
    response = retrieve_worker_result("test", "test")
    assert response is None


@patch("src.utils.query_worker_result", return_value=None)
@patch("src.utils.get_first_query_result", **{"return_value.to_dict.return_value": 1})
@patch("src.utils.get_first_query_result", return_value={"test": "test"})
def test_retrieve_worker_result_2(_a, _b, _c):
    """Test the function retrieve_worker_result."""
    with app.app_context():
        response = retrieve_worker_result("test", "test")
        assert response == 1


def test_get_session_retry():
    """Test get_session_retry."""
    resp = get_session_retry()
    assert resp is not None


@patch("src.utils.update_osio_registered_repos", return_value=None)
def test_update_data_1(a):
    """Test update_data."""
    DatabaseIngestion.update_data(None)


@patch("src.utils.update_osio_registered_repos", side_effect=NoResultFound())
def test_update_data_2(a):
    """Test update_data."""
    with pytest.raises(Exception):
        DatabaseIngestion.update_data(None)
    a.side_effect = SQLAlchemyError()
    with pytest.raises(Exception):
        DatabaseIngestion.update_data(None)


def test_get_store_record():
    """Test get_store_record."""
    with pytest.raises(Exception):
        DatabaseIngestion.store_record({
            "test": "test"
        })


@patch.object(DatabaseIngestion, "get_info", return_value="get_info")
@patch("src.utils.add_entry_to_osio_registered_repos", return_value=None)
def test_get_store_record_1(_a, _b):
    """Test get_store_record."""
    payload = {
        "email-ids": "abcd@gmail.com",
        "git-sha": "somesha",
        "git-url": "test"
    }
    resp = DatabaseIngestion.store_record(payload)
    assert resp == "get_info"


@patch("src.utils.add_entry_to_osio_registered_repos", side_effect=SQLAlchemyError)
def test_get_store_record_2(a):
    """Test get_store_record."""
    with pytest.raises(Exception):
        payload = {
            "email-ids": "abcd@gmail.com",
            "git-sha": "somesha",
            "git-url": "test"
        }
        DatabaseIngestion.store_record(payload)
    a.side_effect = Exception()
    with pytest.raises(Exception):
        payload = {
            "email-ids": "abcd@gmail.com",
            "git-sha": "somesha",
            "git-url": "test"
        }
        DatabaseIngestion.store_record(payload)


def test_get_info():
    """Test get_info."""
    resp = DatabaseIngestion.get_info(None)
    assert resp == {'error': 'No key found', 'is_valid': False}


@patch("src.utils.get_one_result_from_osio_registered_repos",
       side_effect=NoResultFound)
def test_get_info_1(a):
    """Test get_info."""
    resp = DatabaseIngestion.get_info("test")
    assert resp == {'error': 'No information in the records', 'is_valid': False}
    a.side_effect = SQLAlchemyError()
    with pytest.raises(Exception):
        DatabaseIngestion.get_info("test")
    a.side_effect = Exception()
    with pytest.raises(Exception):
        DatabaseIngestion.get_info("test")


@patch("src.utils.init_celery", return_value=None)
@patch("src.utils.run_flow", return_value='dispatcher_id')
def test_server_run_flow(_a, _b):
    """Test server_run_flow."""
    resp = server_run_flow("test", "test")
    assert resp == 'dispatcher_id'


@patch("src.utils.server_run_flow", return_value="d_id")
def test_scan_repo(a):
    """Test scan_repo."""
    payload = {
        "email-ids": "abcd@gmail.com",
        "git-sha": "somesha",
        "git-url": "test"
    }
    resp = scan_repo(payload)
    assert resp is True


def mocked_requests_get_1(*_args, **_kwargs):
    """Mock 1 for requests.get."""
    return MockResponse({"public_key": "test"}, 200, "test")


def mocked_requests_get_2(*_args, **_kwargs):
    """Mock 2 for requests.get."""
    return MockResponse({"public_key": "test"}, 404, "test")


def mocked_requests_get_3(*_args, **_kwargs):
    """Mock 3 for requests.get."""
    return MockResponse({"public_key": "test"}, 500, "test")


@patch("src.utils.requests.get", side_effect=requests.exceptions.Timeout())
def test_fetch_public_key(a):
    """Test fetch_public_key."""
    resp = fetch_public_key(app)
    assert resp == ''


@patch("src.utils.requests.get",
       side_effect=mocked_requests_get_2)
def test_fetch_public_key_1(a):
    """Test fetch_public_key."""
    resp = fetch_public_key(app)
    assert resp == ''


@patch("src.utils.requests.get",
       side_effect=mocked_requests_get_1)
def test_fetch_public_key_2(a):
    """Test fetch_public_key."""
    resp = fetch_public_key(app)
    assert resp == \
        '-----BEGIN PUBLIC KEY-----\ntest\n-----END PUBLIC KEY-----'


@patch("src.utils.requests.get",
       side_effect=mocked_requests_get_3)
def test_fetch_public_key_3(a):
    """Test fetch_public_key."""
    resp = fetch_public_key(app)
    assert resp == \
        '-----BEGIN PUBLIC KEY-----\ntest\n-----END PUBLIC KEY-----'


@patch("src.utils.server_run_flow", return_value="d_id")
def test_alert_user(server_run_flow):
    """Test alert user mechanism."""
    resp = alert_user({
        'git-url': 'git-repo',
        'email-ids': 'dummy'
    }, service_token='test', epv_list=['test'])

    assert resp is True


def test_fix_gremlin_output():
    """Test fix_gremlin_output()."""
    rest_json_path = os.path.join(
        os.path.dirname(__file__),
        'files/fix-gremlin-output'
    )
    with open(rest_json_path) as f:
        resp_json = json.load(f)

        resp = fix_gremlin_output(resp_json)

        resp_data = resp.get('result', {}).get('data', [])
        assert len(resp_data) == 4

        expected = {
            'ch.qos.logback:logback-core': {
                'version': '1.1.0',
                'cves': ['CVE-2017-5929']
            },
            'com.fasterxml.jackson.core:jackson-databind': {
                'version': '2.7.4',
                'cves': ['CVE-2017-15095', 'CVE-2017-7525', 'CVE-2018-5968']
            },
            'com.thoughtworks.xstream:xstream': {
                'version': '1.3',
                'cves': ['CVE-2017-7957', 'CVE-2013-7285', 'CVE-2016-3674']
            },
            'jline:jline': {
                'version': '0.9.94',
                'cves': ['CVE-2013-2035']
            }
        }
        for data in resp_data:
            assert 'epv' in data
            assert 'cves' in data

            assert 'pname' in data['epv']
            assert 'version' in data['epv']

            name = data['epv']['pname'][0]
            version = data['epv']['version'][0]

            cves = [x.get('cve_id')[0] for x in data['cves']]

            assert name in expected
            assert version == expected[name]['version']
            assert cves == expected[name]['cves']

            expected.pop(name)


@patch("src.utils.S3Helper.get_object_content", return_value=mocked_object_response)
def test_generate_comparison(_mock1):
    """Test generate_comparison()."""
    result = generate_comparison(2)
    assert result.get('average_response_time') is not None


class QueryResultMock():
    """Class that mocks QueryResult class."""

    def __init__(self):
        """Initialize the mocked QueryResult class."""
        self.first_called = False

    def first(self):
        """Implement the tested method with tracepoint variable."""
        self.first_called = True
        return "X"

    def get_first_called(self):
        """Return the actual state of tracepoint variable."""
        return self.first_called


def test_get_first_query_result():
    """Test the function get_first_query_result()."""
    query_result_mock = QueryResultMock()
    # make sure the first() was not called
    assert not query_result_mock.get_first_called()

    # this is a value returned by mocked class
    assert get_first_query_result(query_result_mock) == "X"

    # now first() was called, so check it
    assert query_result_mock.get_first_called()


def test_get_parser_from_ecosystem():
    """Test the function get_parser_from_ecosystem()."""
    assert get_parser_from_ecosystem(None) is None
    assert get_parser_from_ecosystem("unknown") is None
    assert get_parser_from_ecosystem("maven").__name__ == MavenParser.__name__
    assert get_parser_from_ecosystem("npm").__name__ == NodeParser.__name__


def test_fetch_records():
    """Test the PostgresPassThrough fetch records module."""
    query = "select id from worker_results limit 1;"
    resp = ppt.fetch_records(data={}, client_validated=False)
    assert resp['warning'] == 'Invalid payload. Check your payload once again'
    resp = ppt.fetch_records(data={'query': {'query': ''}}, client_validated=False)
    assert resp['error'] is not None
    resp = ppt.fetch_records(data={'query': 'delete all from some_table;'}, client_validated=False)
    assert resp['error'] is not None
    data = {'query': query}
    resp = ppt.fetch_records(data, client_validated=False)
    assert resp is not None


graph_resp = {
    "requestId": "5cc29849-8e9b-4b66-90d0-f2569dc962b9",
    "status": {
        "message": "",
        "code": 200,
        "attributes": {}
    },
    "result": {
        "data": [],
        "meta": {}
    }
}


@patch("src.utils.requests.post", return_value=graph_resp)
def test_fetch_nodes(_mock1):
    """Test the GraphPassThrough fetch nodes module."""
    resp = gpt.fetch_nodes(data={})
    assert resp['warning'] == 'Invalid payload. Check your payload once again'
    resp = gpt.fetch_nodes(data={"query": "g.V().has('foo','bar').drop()')"})
    assert resp['error'] is not None
    query = "g.V().has('name','foo').valueMap();"
    resp = gpt.fetch_nodes(data={'query': query})
    assert resp is not None
