from prefect_sqlalchemy import SqlAlchemyConnector

connector = SqlAlchemyConnector(
    connection_url="hive://hive:password@hiveserver2:10000/prefect"
)

connector.save("hive")
