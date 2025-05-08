from prefect import flow, task
import random
import subprocess
from datetime import datetime


@task
def imprimir_mensaje() -> None:
    subprocess.run(["echo", "¡Hola desde Prefect!"], check=True)


@task
def generar_numero() -> None:
    numero = random.randint(1, 100)
    print(f"Número generado: {numero}")


@flow(name="flow_random")
def flow_random_flow() -> None:
    imprimir_mensaje()
    generar_numero()


if __name__ == "__main__":
    flow_random_flow()
