from bkamalie.database.execute import create_tables, insert_fines
from bkamalie.holdsport.api import get_connection
from pytest import fixture
from testcontainers.postgres import PostgresContainer
import polars as pl
from bkamalie.database.model import FineCategory
import streamlit as st


def pytest_addoption(parser):
    parser.addoption(
        "--integration", action="store_true", dest="integration", default=False
    )


def pytest_configure(config):
    if not config.option.integration:
        setattr(config.option, "markexpr", "not integration")
    if config.option.integration:
        setattr(config.option, "markexpr", "integration")


@fixture(scope="session")
def holdsport_con():
    return get_connection(
        st.secrets["holdsport"]["username"], st.secrets["holdsport"]["password"]
    )


@fixture(scope="session")
def df_fines():
    data_input = {
        "id": [1, 2, 3, 4],
        "name": [
            "Late to Training",
            "Red Card",
            "Forgot Equipment",
            "Missed Team Dinner",
        ],
        "fixed_amount": [10, 500, 50, 200],
        "variable_amount": [5, 0, 0, 50],
        "holdbox_amount": [0, 100, 0, 0],
        "description": [
            "Player showed up late to training session.",
            "Player received a red card during match.",
            "Player forgot essential training equipment.",
            "Player missed the mandatory team dinner.",
        ],
        "category": [
            FineCategory.TRAINING.value,
            FineCategory.MATCH.value,
            FineCategory.TRAINING.value,
            FineCategory.OTHER.value,
        ],
    }
    return pl.DataFrame(data_input)


@fixture(scope="session")
def df_members():
    data_input = {
        "id": [1, 2, 3, 4],
        "name": ["Anders And", "Mickey Mouse", "Donald Duck", "Goofy"],
        "role": ["player", "player", "player", "player"],
    }
    return pl.DataFrame(data_input)


postgres = PostgresContainer("postgres:16-alpine")


@fixture(scope="session")
def db_mock(df_fines):
    postgres.start()
    db_con = postgres.get_connection_url()
    db_con = db_con.replace("postgresql+psycopg2", "postgres")
    create_tables(db_con)
    insert_fines(db_con, df_fines.drop("id"))
    return postgres


def pytest_sessionfinish(session, exitstatus):
    """
    Called after whole test run finished, right before
    returning the exit status to the system.
    """
    postgres.stop()
