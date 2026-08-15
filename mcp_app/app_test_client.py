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
            name="getTransactionHistory",
            arguments={
				"account_id": "U24587525",
				"contract_id": 365207014,
			},
        )
        print(result.structured_content)



asyncio.run(main())
