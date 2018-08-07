"""Test module for classes and functions found in the utils module."""
from rest_api import app

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm.exc import NoResultFound

from src.utils import DatabaseIngestion
from src.utils import alert_user, fetch_public_key, get_session, get_session_retry
from src.utils import retrieve_worker_result, scan_repo, server_run_flow, validate_request_data

from unittest.mock import patch
import requests
import pytest


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
        assert response is 1


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
    assert resp is "get_info"


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


@patch("src.utils.server_run_flow", return_value="d_id")
def test_alert_user(server_run_flow):
    """Test alert user mechanism."""
    resp = alert_user({
        'git-url': 'git-repo',
        'email-ids': 'dummy'
    }, service_token='test', epv_list=['test'])

    assert resp is True
