from prefect import flow, task
from hdfs import InsecureClient
import logging

# HDFS client setup
HDFS_URL = "http://namenode:9870"
HDFS_USER = "hdfs"
HDFS_PATH = "/user/prefect/datos.txt"
HDFS_DIR = "/user/prefect"

# Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("prefect.hdfs")


def get_hdfs_client() -> InsecureClient:
    return InsecureClient(url=HDFS_URL, user=HDFS_USER)


@task
def ensure_directory() -> None:
    client = get_hdfs_client()
    if not client.status(HDFS_DIR, strict=False):
        logger.info(f"Creating directory: {HDFS_DIR}")
        client.makedirs(HDFS_DIR)
    else:
        logger.info(f"Directory exists: {HDFS_DIR}")


@task
def write_file() -> None:
    client = get_hdfs_client()
    content = "Este es un archivo de prueba escrito por Prefect en HDFS.\n"
    logger.info(f"Writing to {HDFS_PATH}")
    with client.write(HDFS_PATH, encoding="utf-8", overwrite=True) as writer:
        writer.write(content)


@task
def read_file() -> None:
    client = get_hdfs_client()
    if not client.status(HDFS_PATH, strict=False):
        logger.warning(f"❌ File does not exist: {HDFS_PATH}")
        return
    logger.info(f"Reading from {HDFS_PATH}")
    with client.read(HDFS_PATH, encoding="utf-8") as reader:
        content = reader.read()
        logger.info(f"📄 Content:\n{content}")


@flow(name="flow_hdfs_prefect")
def flow_hdfs_flow() -> None:
    ensure_directory()
    write_file()
    read_file()


if __name__ == "__main__":
    flow_hdfs_flow()
