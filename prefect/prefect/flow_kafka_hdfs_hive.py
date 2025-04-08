import csv
import json
from confluent_kafka import Producer

from typing import NamedTuple
from datetime import datetime, timedelta
import logging

from prefect_sqlalchemy import SqlAlchemyConnector
from prefect import flow, task
from prefect.logging import get_run_logger

KAFKA_TOPIC = "sensores"
HDFS_DIR = "/topics/sensores/partition=0"
HIVE_TABLE = "weather.sensor_data"


conf = {"bootstrap.servers": "kafka:9092"}

producer = Producer(conf)


class Weather(NamedTuple):
    timestamp: str
    temperature_salon: float
    humidity_salon: float
    air_salon: float
    temperature_chambre: float
    humidity_chambre: float
    air_chambre: float
    temperature_bureau: float
    humidity_bureau: float
    air_bureau: float
    temperature_exterieur: float
    humidity_exterieur: float
    air_exterieur: float


@task
def publish_csv():
    logger = get_run_logger()
    try:
        with open(
            "/opt/prefect/resources/home_temperature_and_humidity_smoothed_filled.csv",
            "r",
        ) as file:
            # We need to change timestamp to `timestamp`
            data = csv.DictReader(file)
            weather_data = [Weather(**row) for row in data]
            for register in weather_data:
                producer.produce(
                    KAFKA_TOPIC,
                    json.dumps(register._asdict()).encode("utf-8"),
                )
                producer.poll(0)

        producer.flush()
    except Exception as e:
        logger.error(f"❌ Error al leer el archivo: {e}")
        raise


@task
def create_database():
    logger = get_run_logger()
    with SqlAlchemyConnector.load("hive") as connector:
        connector.execute("CREATE DATABASE IF NOT EXISTS weather")
        logger.info("✅ Base de datos 'weather' creada correctamente en Hive")


@task
def create_table():
    logger = get_run_logger()
    with SqlAlchemyConnector.load("hive") as connector:
        connector.execute(f"""
            CREATE EXTERNAL TABLE IF NOT EXISTS {HIVE_TABLE} (
                `timestamp` DATE,
                temperature_salon FLOAT,
                humidity_salon FLOAT,
                air_salon FLOAT,
                temperature_chambre FLOAT,
                humidity_chambre FLOAT,
                air_chambre FLOAT,
                temperature_bureau FLOAT,
                humidity_bureau FLOAT,
                air_bureau FLOAT,
                temperature_exterieur FLOAT,
                humidity_exterieur FLOAT,
                air_exterieur FLOAT
            )
            ROW FORMAT SERDE 'org.apache.hive.hcatalog.data.JsonSerDe'
            STORED AS TEXTFILE
            LOCATION 'hdfs://namenode:9000{HDFS_DIR}'
        """)
        logger.info("✅ Tabla creada correctamente en Hive")


@task
def query_hive_temps_by_date():
    logger = get_run_logger()
    with SqlAlchemyConnector.load("hive") as connector:
        rows = connector.execute(f"""
             SELECT
             DATE(`timestamp`) AS record_date,
             AVG(temperature_salon) AS avg_temp_salon,
             AVG(temperature_chambre) AS avg_temp_chambre,
             AVG(temperature_bureau) AS avg_temp_bureau,
             AVG(temperature_exterieur) AS avg_temp_exterieur
             FROM {HIVE_TABLE}
             GROUP BY DATE(`timestamp`)
             ORDER BY record_date
        """).fetchall()

        logger.info("Resultados de Hive:")
        logger.info(
            "Fecha | Temp. Salón | Temp. Chambre | Temp. Bureau | Temp. Exterieur"
        )
        for row in rows:
            logger.info(row)


@task
def query_hive_worst_air_quality():
    logger = get_run_logger()
    with SqlAlchemyConnector.load("hive") as connector:
        rows = connector.execute(f"""
             SELECT
             `timestamp`,
             air_salon,
             air_chambre,
             air_bureau,
             air_exterieur,
             GREATEST(air_salon, air_chambre, air_bureau, air_exterieur) AS max_air_quality
             FROM {HIVE_TABLE}
             ORDER BY max_air_quality DESC 
        """).fetchall()

        logger.info("Días con peor calidad de aire en cualquier parte de la casa:")
        logger.info(
            "Fecha | Calidad Salón | Calidad Chambre | Calidad Bureau | Calidad Exterieur"
        )
        for row in rows:
            logger.info(row[:-1])


@task
def query_hive_hummidity_changes():
    logger = get_run_logger()
    with SqlAlchemyConnector.load("hive") as connector:
        rows = connector.execute(f"""
                SELECT
                `timestamp`,
                (1 - (humidity_salon/previous_humidity_salon)) AS change_salon,
                (1 - (humidity_chambre/previous_humidity_chambre)) AS change_chambre,
                (1 - (humidity_bureau/previous_humidity_bureau)) AS change_bureau,
                (1 - (humidity_exterieur/previous_humidity_exterieur)) AS change_exterieur
            FROM (
                SELECT `timestamp`, humidity_salon, humidity_chambre, humidity_bureau, humidity_exterieur,
                    LAG(humidity_salon, 4, humidity_salon) OVER (ORDER BY `timestamp`) AS previous_humidity_salon,
                    LAG(humidity_chambre, 4, humidity_chambre) OVER (ORDER BY `timestamp`) AS previous_humidity_chambre,
                    LAG(humidity_bureau, 4, humidity_bureau) OVER (ORDER BY `timestamp`) AS previous_humidity_bureau,
                    LAG(humidity_exterieur, 4, humidity_exterieur) OVER (ORDER BY `timestamp`) AS previous_humidity_exterieur
                FROM {HIVE_TABLE}
            ) AS t
            WHERE ABS(1 - (humidity_salon/previous_humidity_salon)) > 0.1
                OR ABS(1 - (humidity_chambre/previous_humidity_chambre)) > 0.1
                OR ABS(1 - (humidity_bureau/previous_humidity_bureau)) > 0.1
                OR ABS(1 - (humidity_exterieur/previous_humidity_exterieur)) > 0.1
        """).fetchall()

        logger.info("Resultados de Hive:")
        logger.info(
            "Fecha | Cambio Salón | Cambio Chambre | Cambio Bureau | Cambio Exterieur"
        )
        for row in rows:
            logger.info(row)


# Definición de tareas en Airflow
@flow
def fuck_airflow() -> list:
    publish_csv()
    create_database()
    create_table()
    query_hive_temps_by_date()
    query_hive_worst_air_quality()
    query_hive_hummidity_changes()


if __name__ == "__main__":
    fuck_airflow()
