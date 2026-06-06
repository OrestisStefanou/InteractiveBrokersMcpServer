import asyncio

from interactive_brokers.ib_client import InteractiveBrokersClient
from interactive_brokers.models import SearchContractRequest


async def main():
    client = InteractiveBrokersClient(base_url="https://localhost:5000/v1/api")

    results = await client.search_contract(
        request=SearchContractRequest(symbol="Netflix", name=True)
    )
    print(results)


if __name__ == "__main__":
    asyncio.run(main())
