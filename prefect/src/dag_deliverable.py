import csv
import json

from typing import NamedTuple

from airflow.providers.apache.kafka.operators.produce import ProduceToTopicOperator

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.apache.hive.hooks.hive import HiveServer2Hook
from datetime import datetime, timedelta
import logging

KAFKA_TOPIC = "sensores"
HDFS_DIR = "/topics/sensores/partition=0"
HIVE_TABLE = "weather.sensor_data"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Airflow
default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "start_date": datetime(2025, 3, 18),
    "retries": 1,
    "retry_delay": timedelta(minutes=1),
}
dag = DAG(
    "dag_deliverable",
    default_args=default_args,
    schedule_interval=None,  # Se ejecuta manualmente
    catchup=False,
)


class Weather(NamedTuple):
    record_timestamp: str
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


def publish_csv():
    try:
        with open(
            "/opt/airflow/resources/home_temperature_and_humidity_smoothed_filled.csv",
            "r",
        ) as file:
            # We need to change timestamp to record_timestamp
            data = csv.DictReader(file)
            weather_data = [
                Weather(
                    record_timestamp=row["timestamp"],
                    temperature_salon=float(row["temperature_salon"]),
                    humidity_salon=float(row["humidity_salon"]),
                    air_salon=float(row["air_salon"]),
                    temperature_chambre=float(row["temperature_chambre"]),
                    humidity_chambre=float(row["humidity_chambre"]),
                    air_chambre=float(row["air_chambre"]),
                    temperature_bureau=float(row["temperature_bureau"]),
                    humidity_bureau=float(row["humidity_bureau"]),
                    air_bureau=float(row["air_bureau"]),
                    temperature_exterieur=float(row["temperature_exterieur"]),
                    humidity_exterieur=float(row["humidity_exterieur"]),
                    air_exterieur=float(row["air_exterieur"]),
                )
                for row in data
            ]
            res = []
            for i, row in enumerate(weather_data):
                res.append((f"message_{i}", json.dumps(row._asdict())))
            return res
        return weather_data
    except Exception as e:
        logger.error(f"❌ Error al leer el archivo: {e}")
        raise


# Función para crear la base de datos en Hive
def create_database():
    try:
        hive_hook = HiveServer2Hook(hiveserver2_conn_id="hive_default")
        conn = hive_hook.get_conn()
        cursor = conn.cursor()
        cursor.execute("CREATE DATABASE IF NOT EXISTS weather")
        cursor.close()
        conn.close()
        logger.info("✅ Base de datos 'weather' creada correctamente en Hive")
    except Exception as e:
        logger.error(f"❌ Error al crear la base de datos en Hive: {e}")
        raise


# Función para crear la tabla en Hive
def create_table():
    try:
        hive_hook = HiveServer2Hook(hiveserver2_conn_id="hive_default")
        conn = hive_hook.get_conn()
        cursor = conn.cursor()
        cursor.execute(f"DROP TABLE IF EXISTS {HIVE_TABLE}")
        cursor.execute(f"""
            CREATE EXTERNAL TABLE IF NOT EXISTS {HIVE_TABLE} (
                record_timestamp DATE,
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
        cursor.close()
        conn.close()
        logger.info("✅ Tabla creada correctamente en Hive")
    except Exception as e:
        logger.error(f"❌ Error al crear la tabla en Hive: {e}")
        raise


def query_hive_temps_by_date():
    try:
        hive_hook = HiveServer2Hook(hiveserver2_conn_id="hive_default")
        conn = hive_hook.get_conn()
        cursor = conn.cursor()
        cursor.execute(f"""SELECT
             DATE(record_timestamp) AS record_date,
             AVG(temperature_salon) AS avg_temp_salon,
             AVG(temperature_chambre) AS avg_temp_chambre,
             AVG(temperature_bureau) AS avg_temp_bureau,
             AVG(temperature_exterieur) AS avg_temp_exterieur
             FROM {HIVE_TABLE}
             GROUP BY DATE(record_timestamp)
             ORDER BY record_date
        """)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        logger.info("Resultados de Hive:")
        logger.info(
            "Fecha | Temp. Salón | Temp. Chambre | Temp. Bureau | Temp. Exterieur"
        )
        for row in rows:
            logger.info(row)
    except Exception as e:
        logger.error(f"❌ Error al consultar Hive: {e}")
        raise


def query_hive_worst_air_quality():
    try:
        hive_hook = HiveServer2Hook(hiveserver2_conn_id="hive_default")
        conn = hive_hook.get_conn()
        cursor = conn.cursor()
        cursor.execute(f"""SELECT
             record_timestamp,
             air_salon,
             air_chambre,
             air_bureau,
             air_exterieur,
             GREATEST(air_salon, air_chambre, air_bureau, air_exterieur) AS max_air_quality
             FROM {HIVE_TABLE}
             ORDER BY max_air_quality DESC 
        """)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        logger.info("Días con peor calidad de aire en cualquier parte de la casa:")
        logger.info(
            "Fecha | Calidad Salón | Calidad Chambre | Calidad Bureau | Calidad Exterieur"
        )
        for row in rows:
            logger.info(row[:-1])
    except Exception as e:
        logger.error(f"❌ Error al consultar Hive: {e}")
        raise


def query_hive_hummidity_changes():
    try:
        hive_hook = HiveServer2Hook(hiveserver2_conn_id="hive_default")
        conn = hive_hook.get_conn()
        cursor = conn.cursor()
        # We must use the LAG function to detect when the humidity has changed more than 10% in one hour. Above is an example on how to use the LAG function
        # Measurements are taken every 15 minutes
        cursor.execute(f"""SELECT
                record_timestamp,
                (1 - (humidity_salon/previous_humidity_salon)) AS change_salon,
                (1 - (humidity_chambre/previous_humidity_chambre)) AS change_chambre,
                (1 - (humidity_bureau/previous_humidity_bureau)) AS change_bureau,
                (1 - (humidity_exterieur/previous_humidity_exterieur)) AS change_exterieur
            FROM (
                SELECT record_timestamp, humidity_salon, humidity_chambre, humidity_bureau, humidity_exterieur,
                    LAG(humidity_salon, 4, humidity_salon) OVER (ORDER BY record_timestamp) AS previous_humidity_salon,
                    LAG(humidity_chambre, 4, humidity_chambre) OVER (ORDER BY record_timestamp) AS previous_humidity_chambre,
                    LAG(humidity_bureau, 4, humidity_bureau) OVER (ORDER BY record_timestamp) AS previous_humidity_bureau,
                    LAG(humidity_exterieur, 4, humidity_exterieur) OVER (ORDER BY record_timestamp) AS previous_humidity_exterieur
                FROM {HIVE_TABLE}
            ) AS t
            WHERE ABS(1 - (humidity_salon/previous_humidity_salon)) > 0.1
                OR ABS(1 - (humidity_chambre/previous_humidity_chambre)) > 0.1
                OR ABS(1 - (humidity_bureau/previous_humidity_bureau)) > 0.1
                OR ABS(1 - (humidity_exterieur/previous_humidity_exterieur)) > 0.1
        """)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        logger.info("Resultados de Hive:")
        logger.info(
            "Fecha | Cambio Salón | Cambio Chambre | Cambio Bureau | Cambio Exterieur"
        )
        for row in rows:
            logger.info(row)
    except Exception as e:
        logger.error(f"❌ Error al consultar Hive: {e}")
        raise


# Definición de tareas en Airflow

publish_csv_task = ProduceToTopicOperator(
    task_id="publish_csv",
    topic=KAFKA_TOPIC,
    kafka_config_id="kafka_default",
    producer_function=publish_csv,
    dag=dag,
)

create_database_task = PythonOperator(
    task_id="create_hive_database",
    python_callable=create_database,
    dag=dag,
)

create_table_task = PythonOperator(
    task_id="create_hive_table",
    python_callable=create_table,
    dag=dag,
)

query_hive_temps_by_date_task = PythonOperator(
    task_id="query_hive_temps_by_date",
    python_callable=query_hive_temps_by_date,
    dag=dag,
)

query_hive_worst_air_quality_task = PythonOperator(
    task_id="query_hive_worst_air_quality",
    python_callable=query_hive_worst_air_quality,
    dag=dag,
)

query_hive_hummidity_changes_task = PythonOperator(
    task_id="query_hive_hummidity_changes",
    python_callable=query_hive_hummidity_changes,
    dag=dag,
)

# 🔗 Definir el flujo de ejecución de las tareas
(
    publish_csv_task
    >> create_database_task
    >> create_table_task
    >> query_hive_temps_by_date_task
    >> query_hive_worst_air_quality_task
    >> query_hive_hummidity_changes_task
)
