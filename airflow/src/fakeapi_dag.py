from typing import Any
from datetime import datetime, timedelta

import httpx
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.exceptions import AirflowException, AirflowTaskTimeout


def fetch_fakeapi(**kwargs) -> dict[str, Any]:
    response = None
    try:
        response = httpx.get("http://fake-api/").json()
        if "status_code" in response and response["status_code"] > 400:
            raise AirflowException("API returned an error")
        return response
    except httpx.ReadTimeout:
        raise AirflowTaskTimeout


def show_fakeapi_response(**kwargs) -> None:
    ti = kwargs["ti"]
    response = ti.xcom_pull(task_ids="fetch_fakeapi")
    print(response)


default_args = {
    "owner": "airflow",
    "retries": 3,
    "retry_delay": timedelta(0),
}

with DAG(
    dag_id="show_fakeapi_response_dag",
    default_args=default_args,
    description="Fetch from a fake API and print the response",
    schedule_interval=None,
    start_date=datetime(2023, 1, 1),
    catchup=False,
    tags=["example"],
) as dag:
    fetch_task = PythonOperator(
        task_id="fetch_fakeapi",
        python_callable=fetch_fakeapi,
        provide_context=True,
    )

    print_task = PythonOperator(
        task_id="show_fakeapi_response",
        python_callable=show_fakeapi_response,
        provide_context=True,
    )

    fetch_task >> print_task
