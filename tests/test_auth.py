"""Unit tests for token handling functions."""

import pytest
from unittest.mock import patch
from jwt.contrib.algorithms.pycrypto import RSAAlgorithm

from auth import *


def setup_module(module):
    """Perform setup of any state specific to the execution of the given module."""
    global PRIVATE_KEY
    global PUBLIC_KEY

    # private and public key used in tests
    with open("tests/private_key.pem") as fin:
        PRIVATE_KEY = fin.read()

    with open("tests/public_key.pem") as fin:
        PUBLIC_KEY = fin.read()

    # just to make sure the following statement does not raise an exception
    try:
        jwt.unregister_algorithm('RS256')
    except KeyError:
        pass

    # make sure the RS256 algorithm is initialized
    jwt.register_algorithm('RS256', RSAAlgorithm(RSAAlgorithm.SHA256))


def teardown_module(module):
    """Tear down any specific state."""
    pass


def mocked_fetch_public_key_1(app):
    """Mock for the function fetch_public_key()."""
    return None


def mocked_fetch_public_key_2(app):
    """Mock for the function fetch_public_key()."""
    return "nothing"


def mocked_fetch_public_key_3(app):
    """Mock for the function fetch_public_key()."""
    return PUBLIC_KEY


def mocked_get_audiences():
    """Mock for the function get_audiences()."""
    return []


def mocked_get_audiences_2():
    """Mock for the function get_audiences()."""
    return ["audience1", "audience2"]


def mocked_get_audiences_3():
    """Mock for the function get_audiences()."""
    return ["foo:bar", ]


@patch("auth.get_audiences", side_effect=mocked_get_audiences)
@patch("auth.fetch_public_key", side_effect=mocked_fetch_public_key_1)
def test_decode_token_invalid_input_1(mocked_fetch_public_key, mocked_get_audiences):
    """Test the invalid input handling during token decoding."""
    assert decode_user_token(None) == {}


@patch("auth.get_audiences", side_effect=mocked_get_audiences)
@patch("auth.fetch_public_key", side_effect=mocked_fetch_public_key_1)
def test_decode_token_invalid_input_2(mocked_fetch_public_key, mocked_get_audiences):
    """Test the invalid input handling during token decoding."""
    with pytest.raises(Exception):
        assert decode_user_token("Foobar") is None


@patch("auth.get_audiences", side_effect=mocked_get_audiences)
@patch("auth.fetch_public_key", side_effect=mocked_fetch_public_key_1)
def test_decode_token_invalid_input_3(mocked_fetch_public_key, mocked_get_audiences):
    """Test the invalid input handling during token decoding."""
    with pytest.raises(Exception):
        assert decode_user_token("Bearer ") is None


@patch("auth.get_audiences", side_effect=mocked_get_audiences)
@patch("auth.fetch_public_key", side_effect=mocked_fetch_public_key_2)
def test_decode_token_invalid_input_4(mocked_fetch_public_key, mocked_get_audiences):
    """Test the invalid input handling during token decoding."""
    with pytest.raises(Exception):
        assert decode_user_token("Bearer ") is None


@patch("auth.get_audiences", side_effect=mocked_get_audiences_2)
@patch("auth.fetch_public_key", side_effect=mocked_fetch_public_key_2)
def test_decode_token_invalid_input_5(mocked_fetch_public_key, mocked_get_audiences):
    """Test the handling wrong JWT tokens."""
    with pytest.raises(Exception):
        assert decode_user_token("Bearer something") is None


@patch("auth.get_audiences", side_effect=mocked_get_audiences_3)
@patch("auth.fetch_public_key", side_effect=mocked_fetch_public_key_3)
def test_decode_token_invalid_input_6(mocked_fetch_public_key, mocked_get_audiences):
    """Test the handling wrong JWT tokens."""
    payload = {
        'some': 'payload',
        'aud': 'foo:bar'
    }
    token = jwt.encode(payload, PRIVATE_KEY, algorithm='RS256').decode("utf-8")
    assert decode_user_token(token) is not None


def test_audiences():
    """Test the audiences."""
    assert get_audiences() == ['a', 'b']
