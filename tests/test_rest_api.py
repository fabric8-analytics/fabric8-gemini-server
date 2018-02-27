"""Test module."""
import requests
import os

payload = {
}
port = os.getenv("GEMINI_API_SERVICE_PORT", "5000")

url = "http://localhost:{port}/api/v1".format(port=port)


def test_register_api_endpoint():
    """Test function for register endpoint."""
    pass
