import asyncio

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
            name="getCoinbasePortfolios",
            arguments={
                # "order_request": {
                #     "product_id": "BTC-USDCCC",
                #     "side": "buy",
                #     "base_size": "1",
                # },
                # "end_date": "2025-01-01T01:00:00Z",
            },
        )
        print(result.structured_content)


asyncio.run(main())
