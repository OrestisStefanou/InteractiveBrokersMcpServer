from config import settings
from interactive_brokers.ib_client import InteractiveBrokersClient


def get_interactive_brokers_client() -> InteractiveBrokersClient:
    return InteractiveBrokersClient(
        base_url=settings.interactive_brokers_portal_base_url,
    )
