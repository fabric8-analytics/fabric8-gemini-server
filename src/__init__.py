"""Initiation of public variables."""
import logging
from f8a_worker.setup_celery import init_selinon

logger = logging.getLogger(__name__)

init_selinon()
