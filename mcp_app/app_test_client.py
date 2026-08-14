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

        contract_id = os.environ.get("IB_CONTRACT_ID")
        if contract_id:
            result = await client.call_tool(
                name="getQuotes",
                arguments={"contract_ids": [int(contract_id)]},
            )
            print(result.structured_content)

        # Cancels a live order, so it stays opt-in.
        order_id = os.environ.get("IB_CANCEL_ORDER_ID")
        if order_id:
            result = await client.call_tool(
                name="cancelOrder",
                arguments={
                    "account_id": os.environ["IB_ACCOUNT_ID"],
                    "order_id": order_id,
                },
            )
            print(result.structured_content)


asyncio.run(main())
