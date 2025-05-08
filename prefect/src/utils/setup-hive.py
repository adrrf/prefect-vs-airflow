from prefect_sqlalchemy import SqlAlchemyConnector, ConnectionComponents

try:
    connector = SqlAlchemyConnector(
        connection_info=ConnectionComponents(
            driver="hive",
            username="hive",
            host="hiveserver2",
            port=10000,
        )
    )

    connector.execute("CREATE DATABASE IF NOT EXISTS prefect")

    connector = SqlAlchemyConnector(
        connection_info=ConnectionComponents(
            driver="hive",
            username="hive",
            host="hiveserver2",
            port=10000,
            database="prefect",
        )
    )

    connector.save("hive", overwrite=True)

except Exception as e:
    print(f"Error creating connector: {e}")
    raise
