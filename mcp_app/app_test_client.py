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
            name="getAccountPositions",
            arguments={"account_id": os.environ["IB_ACCOUNT_ID"]},
        )
        print(result.structured_content)


asyncio.run(main())
