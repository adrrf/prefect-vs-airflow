from airflow.plugins_manager import AirflowPlugin
from airflow.models import TaskInstance
from airflow.utils.state import State
from airflow.exceptions import AirflowException
import requests
import os


DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

dags_included = [  # DAGs to include in the plugin
    "show_fakeapi_response_dag",
]


def notify_discord_on_failure(context: dict) -> None:
    task_instance: TaskInstance = context["task_instance"]
    dag_id = context["dag"].dag_id
    task_id = task_instance.task_id
    execution_date = context["execution_date"]
    log_url = context["task_instance"].log_url

    if dag_id not in dags_included:
        pass

    message = {
        "username": "Airflow Fails",
        "embeds": [
            {
                "title": f"❌ DAG `{dag_id}` Failed",
                "description": (
                    f"\tTask `{task_id}`\n"
                    f"\tFailed on `{execution_date}`.\n"
                    f"\t[View logs]({log_url})"
                ),
                "color": 16711680,
            }
        ],
    }

    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=message)
        response.raise_for_status()
    except requests.RequestException as e:
        raise AirflowException(f"Failed to send Discord notification: {e}")


class DiscordFailurePlugin(AirflowPlugin):
    name = "discord_failure_plugin"
    task_failure_callback = notify_discord_on_failure
