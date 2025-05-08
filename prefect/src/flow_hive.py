from prefect_sqlalchemy import SqlAlchemyConnector
from prefect import flow, task
from prefect.logging import get_run_logger


@task
def setup_table(block_name: str) -> None:
    with SqlAlchemyConnector.load(block_name) as connector:
        connector.execute(
            "CREATE TABLE IF NOT EXISTS customers (name STRING, address STRING)"
        )
        connector.execute("INSERT INTO customers VALUES ('Marvin', 'Highway 42')")


@task
def fetch_data(block_name: str) -> list:
    all_rows = []
    with SqlAlchemyConnector.load(block_name) as connector:
        while True:
            # Repeated fetch* calls using the same operation will
            # skip re-executing and instead return the next set of results
            new_rows = connector.fetch_many("SELECT * FROM customers", size=2)
            if len(new_rows) == 0:
                break
            all_rows.append(new_rows)
    return all_rows


@flow
def sqlalchemy_flow(block_name: str) -> list:
    logger = get_run_logger()
    setup_table(block_name)
    all_rows = fetch_data(block_name)
    logger.info(f"Fetched rows: {all_rows}")
    return all_rows


if __name__ == "__main__":
    sqlalchemy_flow("hive")
