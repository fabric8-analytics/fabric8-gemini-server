"""Sends notification to users."""

import os
from time import strftime, gmtime
from uuid import uuid4

import requests
import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class UserNotification:
    """Generates report containing descriptive data for dependencies."""

    @staticmethod
    def send_notification(notification, token):
        """Send notification to the OSIO notification service."""
        url = os.getenv('NOTIFICATION_SERVICE_HOST', '').strip()

        endpoint = '{url}/api/notify'.format(url=url)
        auth = 'Bearer {token}'.format(token=token)
        resp = requests.post(endpoint, json=notification, headers={'Authorization': auth})
        if resp.status_code == 202:
            return {'status': 'success'}
        else:
            if resp.status_code == 401:
                return {'status': 'failure', 'status_code': resp.status_code}
            else:
                resp.raise_for_status()

    @staticmethod
    def generate_notification(report):
        """Generate notification structure from the cve report."""
        result = {
            "data": {
                "attributes": {
                    "custom": report,
                    "id": report.get('repo_url', ""),
                    "type": "analytics.notify.cve"
                },
                "id": str(uuid4()),
                "type": "notifications"
            }
        }
        result["data"]["attributes"]["custom"]["scanned_at"] = \
            strftime("%a, %d %B %Y %T GMT", gmtime())
        vulnerable_deps = result["data"]["attributes"]["custom"]["vulnerable_deps"]
        del result["data"]["attributes"]["custom"]["vulnerable_deps"]
        total_cve_count = 0
        transitive_updates = list()
        direct_updates = list()

        for deps in vulnerable_deps:
            is_transitive = deps.get("is_transitive", None)
            if is_transitive:
                transitive_updates.append(deps)
            else:
                direct_updates.append(deps)
            total_cve_count += int(deps['cve_count'])
        result["data"]["attributes"]["custom"]["total_dependencies"] = len(vulnerable_deps)
        result["data"]["attributes"]["custom"]["cve_count"] = total_cve_count
        result["data"]["attributes"]["custom"]["transitive_updates"] = transitive_updates
        result["data"]["attributes"]["custom"]["direct_updates"] = direct_updates
        logger.error("Notification Payload %s", result)
        return result
