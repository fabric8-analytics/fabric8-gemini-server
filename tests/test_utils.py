"""Test module for classes and functions found in the utils module."""
import requests
import os

from src.utils import *


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


if __name__ == '__main__':
    test_validate_request_data()
