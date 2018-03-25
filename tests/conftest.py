"""Definition of fixtures for static data, sessions etc. used by unit tests."""

import os

from flask import current_app
from f8a_worker.models import OSIORegisteredRepos, WorkerResult
from sqlalchemy import create_engine
from f8a_worker.models import Base
import pytest

from src.rest_api import *


@pytest.fixture
def client():
    """Provide the client session used by tests."""
    with app.test_client() as client:
        yield client


def create_database():
    """Help method to create database."""
    con_string = 'postgresql://{user}:{passwd}@{pg_host}:' + \
                 '{pg_port}/{db}?sslmode=disable'
    connection = con_string.format(
        user=os.getenv('POSTGRESQL_USER'),
        passwd=os.getenv('POSTGRESQL_PASSWORD'),
        pg_host=os.getenv(
            'PGBOUNCER_SERVICE_HOST',
            'bayesian-pgbouncer'),
        pg_port=os.getenv(
            'PGBOUNCER_SERVICE_PORT',
            '5432'),
        db=os.getenv('POSTGRESQL_DATABASE'))
    engine = create_engine(connection)
    Base.metadata.drop_all(engine)
    OSIORegisteredRepos.__table__.create(engine)
    WorkerResult.__table__.create(engine)
