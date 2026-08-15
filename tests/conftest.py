import pytest

from config import settings

BASE_URL = "https://localhost:5000/v1/api"


@pytest.fixture(autouse=True)
def ib_base_url(monkeypatch):
    monkeypatch.setattr(
        settings,
        "interactive_brokers_portal_base_url",
        BASE_URL,
    )
    return BASE_URL
