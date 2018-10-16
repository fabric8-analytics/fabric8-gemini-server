"""Tests for UserNotification."""

from src.notification.user_notification import UserNotification


def test_generate_notification():
    """Test generate notification."""
    report = {
        "repo_url": "http://test",
        "vulnerable_deps": [
            {
                "cve_count": 0
            },
            {
                "cve_count": 1
            }
        ],
        "cve_count": 0
    }
    resp = UserNotification.generate_notification(report)
    assert resp["data"]["attributes"]["custom"]["cve_count"] == 1


def test_generate_notification_2():
    """Test generate notification."""
    report = {
        "repo_url": "http://test",
        "vulnerable_deps": [
            {
                "cve_count": 1
            },
            {
                "cve_count": 0
            }
        ],
        "cve_count": 0
    }
    resp = UserNotification.generate_notification(report)
    assert resp["data"]["attributes"]["custom"]["cve_count"] == 1


def test_generate_notification_3():
    """Test generate notification."""
    report = {
        "repo_url": "http://test",
        "vulnerable_deps": [
            {
                "cve_count": 1
            },
            {
                "cve_count": 1
            }
        ],
        "cve_count": 0
    }
    resp = UserNotification.generate_notification(report)
    assert resp["data"]["attributes"]["custom"]["cve_count"] == 2
