"""Test RepoDependencyCreator."""

from src.repo_dependency_creator import RepoDependencyCreator
from pathlib import Path
import json
import pytest
from unittest import mock


def test_generate_report():
    """Test the method RepoDependencyCreator.generate_report."""
    with (Path(__file__).parent / "files/report.json").open(encoding='utf-8') as f:
        content = json.load(f)
        response = RepoDependencyCreator.generate_report(content, deps_list={})
        assert response is not []
        assert len(response) == 1

        assert "repo_url" in response[0]
        assert "vulnerable_deps" in response[0]

        assert response[0]["repo_url"] == 'https://github.com/abs51295/maven-simple.git'
        assert response[0]["vulnerable_deps"] == []


def check_gremlin_payload(payload):
    """Check for the payload send to Gremlin."""
    assert payload is not None
    assert "gremlin" in payload
    assert payload["gremlin"].startswith("repo=g.V()")
    assert "test_repository" in payload["gremlin"]


def mock_post_with_payload_check(*_args, **kwargs):
    """Mock the call to the Gremlin service."""
    class MockResponse:
        """Mock response object."""

        def __init__(self, json_data, status_code):
            """Create a mock json response."""
            self.json_data = json_data
            self.status_code = status_code

        def json(self):
            """Get the mock json response."""
            return self.json_data

    payload = kwargs["json"]
    check_gremlin_payload(payload)

    # return the empty payload send to the mocked service
    resp = {}
    return MockResponse(resp, 200)


def mock_post_with_error_status_code(*_args, **kwargs):
    """Mock the call to the Gremlin service."""
    class MockResponse:
        """Mock response object."""

        def __init__(self, json_data, status_code):
            """Create a mock json response."""
            self.json_data = json_data
            self.status_code = status_code

        def json(self):
            """Get the mock json response."""
            return self.json_data

    payload = kwargs["json"]
    check_gremlin_payload(payload)

    # return the empty payload send to the mocked service
    resp = {}
    return MockResponse(resp, 404)


@mock.patch('requests.post', side_effect=mock_post_with_payload_check)
def test_create_repo_node_and_get_cve(_mock_post):
    """Test the method RepoDependencyCreator.create_repo_node_and_get_cve."""
    github_repo = "test_repository"

    # direct dependencies list is empty
    # transitive dependencies list is empty as well
    deps_list = {"direct": [],
                 "transitive": []}

    x = RepoDependencyCreator.create_repo_node_and_get_cve(github_repo, deps_list)
    assert x is not None


@mock.patch('requests.post', side_effect=mock_post_with_payload_check)
def test_create_repo_node_and_get_cve_direct_dependency(_mock_post):
    """Test the method RepoDependencyCreator.create_repo_node_and_get_cve."""
    github_repo = "test_repository"

    # only direct dependency list is filled in
    # transitive dependencies list is empty
    deps_list = {"direct": ["xxx:yyy:zzz:www"],
                 "transitive": []}

    x = RepoDependencyCreator.create_repo_node_and_get_cve(github_repo, deps_list)
    assert x is not None


@mock.patch('requests.post', side_effect=mock_post_with_payload_check)
def test_create_repo_node_and_get_cve_direct_dependency_epv_only(_mock_post):
    """Test the method RepoDependencyCreator.create_repo_node_and_get_cve."""
    github_repo = "test_repository"

    # use EPV only in direct dependencies
    deps_list = {"direct": ["xxx:yyy:zzz"],
                 "transitive": []}

    x = RepoDependencyCreator.create_repo_node_and_get_cve(github_repo, deps_list)
    assert x is not None


@mock.patch('requests.post', side_effect=mock_post_with_payload_check)
def test_create_repo_node_and_get_cve_direct_dependencies(_mock_post):
    """Test the method RepoDependencyCreator.create_repo_node_and_get_cve."""
    github_repo = "test_repository"

    # only direct dependency list is filled in
    # transitive dependencies list is empty
    deps_list = {"direct": ["xxx:yyy:zzz:www", "x2:y2:z2:w2"],
                 "transitive": []}

    x = RepoDependencyCreator.create_repo_node_and_get_cve(github_repo, deps_list)
    assert x is not None
