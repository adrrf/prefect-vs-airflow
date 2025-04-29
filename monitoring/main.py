from typing import Dict

import requests

PROMETHEUS_URL = "http://prometheus:9090/api/v1/query"
QUERY_RANGE_URL = "http://prometheus:9090/api/v1/query_range"

CPU_QUERY = (
    'sum(rate(container_cpu_usage_seconds_total{name=~".+"}[5m])) by (name) * 100'
)

MEM_QUERY = 'sum(container_memory_rss{name=~".+"}) by (name)'


def query_range(
    prometheus_url: str, query: str, start: str, end: str, step: str
) -> Dict:
    payload = {"query": query, "start": start, "end": end, "step": step}
    response = requests.post(prometheus_url, data=payload)
    response.raise_for_status()
    return response.json()


def query(prometheus_url: str, query: str) -> Dict:
    payload = {"query": query}
    response = requests.post(prometheus_url, data=payload)
    response.raise_for_status()
    return response.json()


def cpu_usage(instant: bool, start: str, end: str, step: str):
    if instant:
        return query(PROMETHEUS_URL, CPU_QUERY)
    else:
        return query_range(QUERY_RANGE_URL, CPU_QUERY, start, end, step)


def memory_usage(instant: bool, start: str, end: str, step: str):
    if instant:
        return query(PROMETHEUS_URL, MEM_QUERY)
    else:
        return query_range(QUERY_RANGE_URL, MEM_QUERY, start, end, step)
