from prefect import flow, task
from confluent_kafka import Producer, Consumer, KafkaError
import json
import logging
from typing import List, Tuple

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("prefect.kafka")

KAFKA_TOPIC = "test_topic"
KAFKA_CONFIG = {"bootstrap.servers": "kafka:9092"}

producer = Producer(KAFKA_CONFIG)


@task
def produce_messages() -> List[Tuple[str, str]]:
    """Generate and send 10 messages to Kafka topic as (key, value) pairs."""
    messages = [
        (
            f"mensaje_{i}",
            json.dumps({"mensaje": f"¡Mensaje {i} desde Prefect y Kafka!"}).encode(
                "utf-8"
            ),
        )
        for i in range(10)
    ]
    logger.info(f"📤 Enviando {len(messages)} mensajes a Kafka...")

    for key, value in messages:
        producer.produce(KAFKA_TOPIC, key=key.encode(), value=value.encode())
        producer.poll(0)
    producer.flush()
    return messages


@task
def count_messages(messages: List[Tuple[str, str]]) -> None:
    """Count number of messages sent."""
    count = len(messages) if messages else 0
    logger.info(f"📊 Se han generado {count} mensajes en Kafka.")


@flow(name="flow_kafka")
def kafka_flow() -> None:
    messages = produce_messages()
    count_messages(messages)


if __name__ == "__main__":
    kafka_flow()
