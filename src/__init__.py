"""Initiation of public variables."""
import logging

logger = logging.getLogger(__name__)

from f8a_worker.setup_celery import init_selinon

init_selinon()