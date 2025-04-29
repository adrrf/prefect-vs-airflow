from typing import Any
from datetime import timedelta

import httpx
from prefect import flow, task
from prefect.cache_policies import INPUTS
from prefect.concurrency.sync import rate_limit


@task(retries=3, cache_policy=INPUTS)
def fetch_fakeapi() -> dict[str, Any]:
    response = httpx.get("http://fake-api/").json()
    # Make the flow fail if status is greater than 400
    if "status_code" in response and response["status_code"] > 400:
        raise ValueError("API returned an error")
    return response


@flow(log_prints=True)
def show_fakeapi_response() -> None:
    response = fetch_fakeapi()

    print(f"{response}")


if __name__ == "__main__":
    show_fakeapi_response()
