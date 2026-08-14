import asyncio
import os

from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

transport = StreamableHttpTransport(
    url="http://127.0.0.1:9092/mcp",
)

# HTTP server
client = Client(transport)


async def main():
    async with client:
        # Basic server interaction
        await client.ping()

        result = await client.call_tool(
            name="getTrades",
            arguments={"account_id": os.environ["IB_ACCOUNT_ID"], "days": 7},
        )
        print(result.structured_content)

        contract_id = os.environ.get("IB_CONTRACT_ID")
        if contract_id:
            result = await client.call_tool(
                name="getTransactionHistory",
                arguments={
                    "account_id": os.environ["IB_ACCOUNT_ID"],
                    "contract_id": int(contract_id),
                },
            )
            print(result.structured_content)


asyncio.run(main())
