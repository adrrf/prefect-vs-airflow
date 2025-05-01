from datetime import timedelta
from plugins.task_failure_notify import notify_discord_on_failure

default_args = {
    "owner": "airflow",
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
    "on_failure_callback": notify_discord_on_failure,
}
