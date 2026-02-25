import pytest
from testcontainers.postgres import PostgresContainer


@pytest.fixture(scope="session")
def pg_container():
    """Start a PostgreSQL + pgvector container for the test session."""
    with PostgresContainer(
        image="pgvector/pgvector:pg16",
        username="test",
        password="test",
        dbname="flux_test",
    ) as pg:
        yield pg


@pytest.fixture(scope="session")
def pg_url(pg_container):
    """Return the PostgreSQL connection URL."""
    return pg_container.get_connection_url().replace("+psycopg2", "")
