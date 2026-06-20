try:
    import requests
    RequestException = requests.RequestException
except ModuleNotFoundError:  # pragma: no cover - only used in minimal test envs
    class RequestException(Exception):
        pass

    class _MissingRequests:
        def post(self, *_args, **_kwargs):
            raise RequestException("The requests package is required for dashboard API calls.")

    requests = _MissingRequests()

from src.dashboard.config import API_BASE_URL


def simulate(payload):
    response = requests.post(
        f"{API_BASE_URL}/api/simulate",
        json=payload
    )
    response.raise_for_status()
    return response.json()


def compare(payload):
    response = requests.post(
        f"{API_BASE_URL}/api/compare",
        json=payload
    )
    response.raise_for_status()
    return response.json()


def recommendations(payload):
    response = requests.post(
        f"{API_BASE_URL}/api/recommendations",
        json=payload
    )
    response.raise_for_status()
    return response.json()


def report(payload):
    response = requests.post(
        f"{API_BASE_URL}/api/report",
        json=payload
    )
    response.raise_for_status()
    return response.json()


def network_info(payload):
    response = requests.post(
        f"{API_BASE_URL}/api/network-info",
        json=payload
    )
    response.raise_for_status()
    return response.json()
