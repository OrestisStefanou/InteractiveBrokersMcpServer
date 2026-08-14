import httpx
import pytest
import respx
from fastmcp import Client
from fastmcp.exceptions import ToolError

import mcp_app.app
from interactive_brokers.ib_client import InteractiveBrokersClient
from tests.conftest import BASE_URL

CONTRACT_ID = 265598
SNAPSHOT_URL = f"{BASE_URL}/iserver/marketdata/snapshot"

LIVE_SNAPSHOT = [
    {
        "conid": CONTRACT_ID,
        "55": "AAPL",
        "7051": "APPLE INC",
        "31": "231.44",
        "84": "231.40",
        "86": "231.48",
        "88": "300",
        "85": "500",
        "7295": "230.10",
        "7296": "229.80",
        "7762": "51234567",
        "6509": "RB",
        "_updated": 1755190401000,
    }
]


@pytest.fixture
def ib_client() -> InteractiveBrokersClient:
    return InteractiveBrokersClient(base_url=BASE_URL)


@pytest.fixture
def mcp_client() -> Client:
    return Client(mcp_app.app.mcp_app)


@pytest.fixture(autouse=True)
def no_warmup_delay(monkeypatch):
    # The client sleeps between the warm-up request and the retry.
    monkeypatch.setattr(
        "interactive_brokers.ib_client.SNAPSHOT_WARMUP_DELAY_SECONDS", 0.0
    )


@respx.mock
async def test_get_snapshot_requests_quote_fields(ib_client):
    route = respx.get(SNAPSHOT_URL).mock(
        return_value=httpx.Response(200, json=LIVE_SNAPSHOT)
    )

    await ib_client.get_market_data_snapshot([CONTRACT_ID, 272093])

    params = route.calls.last.request.url.params
    assert params["conids"] == f"{CONTRACT_ID},272093"
    requested = params["fields"].split(",")
    # Bid and ask are the point of the call.
    assert "84" in requested
    assert "86" in requested


@respx.mock
async def test_get_snapshot_retries_when_subscription_is_cold(ib_client):
    route = respx.get(SNAPSHOT_URL).mock(
        side_effect=[
            # IB answers the first request with the subscription only.
            httpx.Response(200, json=[{"conid": CONTRACT_ID, "_updated": 1}]),
            httpx.Response(200, json=LIVE_SNAPSHOT),
        ]
    )

    results = await ib_client.get_market_data_snapshot([CONTRACT_ID])

    assert route.call_count == 2
    assert results[0].bid_price == "231.40"


@respx.mock
async def test_get_snapshot_does_not_retry_when_data_arrives(ib_client):
    route = respx.get(SNAPSHOT_URL).mock(
        return_value=httpx.Response(200, json=LIVE_SNAPSHOT)
    )

    await ib_client.get_market_data_snapshot([CONTRACT_ID])

    assert route.call_count == 1


@respx.mock
async def test_get_snapshot_retries_on_empty_body(ib_client):
    route = respx.get(SNAPSHOT_URL).mock(
        side_effect=[
            httpx.Response(200, json=[]),
            httpx.Response(200, json=LIVE_SNAPSHOT),
        ]
    )

    results = await ib_client.get_market_data_snapshot([CONTRACT_ID])

    assert route.call_count == 2
    assert len(results) == 1


@respx.mock
async def test_get_snapshot_raises_on_http_error(ib_client):
    respx.get(SNAPSHOT_URL).mock(return_value=httpx.Response(500, text="boom"))

    with pytest.raises(httpx.HTTPStatusError):
        await ib_client.get_market_data_snapshot([CONTRACT_ID])


@respx.mock
async def test_quotes_tool_maps_live_quote(mcp_client):
    respx.get(SNAPSHOT_URL).mock(return_value=httpx.Response(200, json=LIVE_SNAPSHOT))

    async with mcp_client:
        result = await mcp_client.call_tool(
            name="getQuotes", arguments={"contract_ids": [CONTRACT_ID]}
        )

    quotes = result.structured_content["result"]
    assert len(quotes) == 1

    quote = quotes[0]
    assert quote["contract_id"] == CONTRACT_ID
    assert quote["symbol"] == "AAPL"
    assert quote["company_name"] == "APPLE INC"
    assert quote["bid_price"] == 231.40
    assert quote["ask_price"] == 231.48
    assert quote["bid_size"] == 300.0
    assert quote["ask_size"] == 500.0
    assert quote["last_price"] == 231.44
    assert quote["previous_close"] == 229.80
    assert quote["volume"] == 51234567.0
    assert quote["data_availability"] == "RB"
    assert quote["is_delayed"] is False
    assert quote["is_stale"] is False
    assert quote["is_halted"] is False
    assert quote["updated_at"] == 1755190401000


@respx.mock
async def test_quotes_tool_derives_spread(mcp_client):
    respx.get(SNAPSHOT_URL).mock(return_value=httpx.Response(200, json=LIVE_SNAPSHOT))

    async with mcp_client:
        result = await mcp_client.call_tool(
            name="getQuotes", arguments={"contract_ids": [CONTRACT_ID]}
        )

    assert result.structured_content["result"][0]["spread"] == pytest.approx(0.08)


@respx.mock
async def test_quotes_tool_leaves_spread_null_without_both_sides(mcp_client):
    respx.get(SNAPSHOT_URL).mock(
        return_value=httpx.Response(
            200, json=[{**LIVE_SNAPSHOT[0], "86": None}]
        )
    )

    async with mcp_client:
        result = await mcp_client.call_tool(
            name="getQuotes", arguments={"contract_ids": [CONTRACT_ID]}
        )

    quote = result.structured_content["result"][0]
    assert quote["ask_price"] is None
    assert quote["spread"] is None


@respx.mock
async def test_quotes_tool_flags_previous_close_as_stale(mcp_client):
    respx.get(SNAPSHOT_URL).mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    **LIVE_SNAPSHOT[0],
                    # IB prefixes a carried-over close with C.
                    "84": "C229.75",
                    "86": "C229.85",
                    "31": "C229.80",
                }
            ],
        )
    )

    async with mcp_client:
        result = await mcp_client.call_tool(
            name="getQuotes", arguments={"contract_ids": [CONTRACT_ID]}
        )

    quote = result.structured_content["result"][0]
    # The prefix must not leak into the number, and must not be dropped silently.
    assert quote["bid_price"] == 229.75
    assert quote["ask_price"] == 229.85
    assert quote["is_stale"] is True


@respx.mock
async def test_quotes_tool_flags_halted(mcp_client):
    respx.get(SNAPSHOT_URL).mock(
        return_value=httpx.Response(
            200, json=[{**LIVE_SNAPSHOT[0], "31": "H231.44"}]
        )
    )

    async with mcp_client:
        result = await mcp_client.call_tool(
            name="getQuotes", arguments={"contract_ids": [CONTRACT_ID]}
        )

    quote = result.structured_content["result"][0]
    assert quote["last_price"] == 231.44
    assert quote["is_halted"] is True


@respx.mock
async def test_quotes_tool_flags_delayed_data(mcp_client):
    respx.get(SNAPSHOT_URL).mock(
        return_value=httpx.Response(200, json=[{**LIVE_SNAPSHOT[0], "6509": "DP"}])
    )

    async with mcp_client:
        result = await mcp_client.call_tool(
            name="getQuotes", arguments={"contract_ids": [CONTRACT_ID]}
        )

    assert result.structured_content["result"][0]["is_delayed"] is True


@respx.mock
async def test_quotes_tool_reports_unknown_availability_as_null(mcp_client):
    payload = {k: v for k, v in LIVE_SNAPSHOT[0].items() if k != "6509"}
    respx.get(SNAPSHOT_URL).mock(return_value=httpx.Response(200, json=[payload]))

    async with mcp_client:
        result = await mcp_client.call_tool(
            name="getQuotes", arguments={"contract_ids": [CONTRACT_ID]}
        )

    quote = result.structured_content["result"][0]
    assert quote["is_delayed"] is None
    assert quote["data_availability"] is None


@respx.mock
async def test_quotes_tool_survives_unparseable_price(mcp_client):
    respx.get(SNAPSHOT_URL).mock(
        return_value=httpx.Response(200, json=[{**LIVE_SNAPSHOT[0], "31": "n/a"}])
    )

    async with mcp_client:
        result = await mcp_client.call_tool(
            name="getQuotes", arguments={"contract_ids": [CONTRACT_ID]}
        )

    quote = result.structured_content["result"][0]
    assert quote["last_price"] is None
    assert quote["bid_price"] == 231.40


@respx.mock
async def test_quotes_tool_rejects_empty_request(mcp_client):
    async with mcp_client:
        with pytest.raises(ToolError, match="At least one contract id"):
            await mcp_client.call_tool(
                name="getQuotes", arguments={"contract_ids": []}
            )


@respx.mock
async def test_quotes_tool_rejects_oversized_request(mcp_client):
    async with mcp_client:
        with pytest.raises(ToolError, match="At most 50 contract ids"):
            await mcp_client.call_tool(
                name="getQuotes", arguments={"contract_ids": list(range(51))}
            )
