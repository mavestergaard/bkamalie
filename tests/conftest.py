from holdsport.api import get_connection
from pytest import fixture
import os
from testcontainers.postgres import PostgresContainer
import pathlib
import polars as pl
from database.model import Fine, FineCategory, RecordedFine


def pytest_addoption(parser):
    parser.addoption("--integration", action="store_true", dest="integration", default=False)


def pytest_configure(config):
    if not config.option.integration:
        setattr(config.option, "markexpr", "not integration")
    if config.option.integration:
        setattr(config.option, "markexpr", "integration")


@fixture(scope="session")
def holdsport_con():
    return get_connection(username,password)

@fixture(scope="session")
def df_fines():
    data_input = {
        "id": [1, 2, 3, 4],
        "name": ["Late to Training", "Red Card", "Forgot Equipment", "Missed Team Dinner"],
        "fixed_amount": [100, 500, 50, 200],
        "varible_amount": [0, 0, 0, 50],
        "holdbox_amount": [0, 100, 0, 0],
        "description": [
            "Player showed up late to training session.",
            "Player received a red card during match.",
            "Player forgot essential training equipment.",
            "Player missed the mandatory team dinner."
        ],
        "category": [
            FineCategory.TRAINING.value,
            FineCategory.MATCH.value,
            FineCategory.TRAINING.value,
            FineCategory.OTHER.value
        ]
    }
    return pl.DataFrame(data_input)


@fixture(scope="session")
def db_mock():
    postgres = PostgresContainer("postgres:16-alpine")
    postgres.start()
    return postgres


def pytest_sessionfinish(session, exitstatus):
    """
    Called after whole test run finished, right before
    returning the exit status to the system.
    """
    postgres.stop()
