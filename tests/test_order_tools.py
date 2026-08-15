import importlib
import json

import httpx
import pytest
import respx
from fastmcp import Client
from fastmcp.exceptions import ToolError

import mcp_app.app
from tests.conftest import BASE_URL

ACCOUNT_ID = "DU1234567"
ORDERS_URL = f"{BASE_URL}/iserver/account/{ACCOUNT_ID}/orders"
CONTRACT_ID = 265598

PLACE_ORDER_ARGS = {
    "account_id": ACCOUNT_ID,
    "contract_id": CONTRACT_ID,
    "side": "BUY",
    "quantity": 1,
}


@pytest.fixture
def mcp_client() -> Client:
    return Client(mcp_app.app.mcp_app)


@respx.mock
async def test_place_order_returns_submitted(mcp_client):
    respx.post(ORDERS_URL).mock(
        return_value=httpx.Response(
            200, json=[{"order_id": "1234", "order_status": "PreSubmitted"}]
        )
    )

    async with mcp_client:
        result = await mcp_client.call_tool(name="placeOrder", arguments=PLACE_ORDER_ARGS)

    orders = result.structured_content["result"]
    assert len(orders) == 1
    assert orders[0]["status"] == "SUBMITTED"
    assert orders[0]["order_id"] == "1234"
    assert orders[0]["order_status"] == "PreSubmitted"
    assert orders[0]["reply_id"] is None


@respx.mock
async def test_place_order_returns_needs_confirmation(mcp_client):
    respx.post(ORDERS_URL).mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "id": "reply-1",
                    "message": ["Your order size is above the typical size."],
                }
            ],
        )
    )

    async with mcp_client:
        result = await mcp_client.call_tool(name="placeOrder", arguments=PLACE_ORDER_ARGS)

    order = result.structured_content["result"][0]
    assert order["status"] == "NEEDS_CONFIRMATION"
    assert order["reply_id"] == "reply-1"
    assert order["messages"] == ["Your order size is above the typical size."]
    assert order["order_id"] is None


@respx.mock
async def test_place_order_returns_rejected(mcp_client):
    respx.post(ORDERS_URL).mock(
        return_value=httpx.Response(200, json=[{"error": "Contract is not tradable"}])
    )

    async with mcp_client:
        result = await mcp_client.call_tool(name="placeOrder", arguments=PLACE_ORDER_ARGS)

    order = result.structured_content["result"][0]
    assert order["status"] == "REJECTED"
    assert order["error"] == "Contract is not tradable"


@respx.mock
async def test_place_order_returns_unknown_on_empty_response(mcp_client):
    respx.post(ORDERS_URL).mock(return_value=httpx.Response(200, json=[{}]))

    async with mcp_client:
        result = await mcp_client.call_tool(name="placeOrder", arguments=PLACE_ORDER_ARGS)

    assert result.structured_content["result"][0]["status"] == "UNKNOWN"


@respx.mock
async def test_place_order_sends_market_order_with_generated_client_order_id(mcp_client):
    route = respx.post(ORDERS_URL).mock(
        return_value=httpx.Response(200, json=[{"order_id": "1234"}])
    )

    async with mcp_client:
        result = await mcp_client.call_tool(
            name="placeOrder",
            arguments=PLACE_ORDER_ARGS | {"side": "SELL", "time_in_force": "IOC"},
        )

    sent_order = json.loads(route.calls.last.request.content)["orders"][0]
    assert sent_order["orderType"] == "MKT"
    assert sent_order["side"] == "SELL"
    assert sent_order["tif"] == "IOC"
    assert "price" not in sent_order

    client_order_id = result.structured_content["result"][0]["client_order_id"]
    assert client_order_id == sent_order["c_oid"]


@respx.mock
async def test_place_order_client_order_id_is_unique_per_call(mcp_client):
    respx.post(ORDERS_URL).mock(return_value=httpx.Response(200, json=[{"order_id": "1"}]))

    async with mcp_client:
        first = await mcp_client.call_tool(name="placeOrder", arguments=PLACE_ORDER_ARGS)
        second = await mcp_client.call_tool(name="placeOrder", arguments=PLACE_ORDER_ARGS)

    assert (
        first.structured_content["result"][0]["client_order_id"]
        != second.structured_content["result"][0]["client_order_id"]
    )


@respx.mock
async def test_place_order_unreadable_response_reports_possible_placement(mcp_client):
    respx.post(ORDERS_URL).mock(
        return_value=httpx.Response(200, json={"error": "unexpected shape"})
    )

    async with mcp_client:
        with pytest.raises(ToolError) as exc_info:
            await mcp_client.call_tool(name="placeOrder", arguments=PLACE_ORDER_ARGS)

    assert "may already be placed" in str(exc_info.value)


@respx.mock
async def test_confirm_order_submits_reply(mcp_client):
    route = respx.post(f"{BASE_URL}/iserver/reply/reply-1").mock(
        return_value=httpx.Response(
            200, json=[{"order_id": "1234", "order_status": "Submitted"}]
        )
    )

    async with mcp_client:
        result = await mcp_client.call_tool(
            name="confirmOrder",
            arguments={"reply_id": "reply-1"},
        )

    assert json.loads(route.calls.last.request.content) == {"confirmed": True}
    order = result.structured_content["result"][0]
    assert order["status"] == "SUBMITTED"
    assert order["order_id"] == "1234"
    assert order["client_order_id"] is None


@respx.mock
async def test_confirm_order_declines(mcp_client):
    route = respx.post(f"{BASE_URL}/iserver/reply/reply-1").mock(
        return_value=httpx.Response(200, json=[{"order_id": "1234"}])
    )

    async with mcp_client:
        await mcp_client.call_tool(
            name="confirmOrder",
            arguments={"reply_id": "reply-1", "confirmed": False},
        )

    assert json.loads(route.calls.last.request.content) == {"confirmed": False}


@respx.mock
async def test_confirm_order_returns_further_warning(mcp_client):
    respx.post(f"{BASE_URL}/iserver/reply/reply-1").mock(
        return_value=httpx.Response(
            200, json=[{"id": "reply-2", "message": ["Are you sure?"]}]
        )
    )

    async with mcp_client:
        result = await mcp_client.call_tool(
            name="confirmOrder",
            arguments={"reply_id": "reply-1"},
        )

    order = result.structured_content["result"][0]
    assert order["status"] == "NEEDS_CONFIRMATION"
    assert order["reply_id"] == "reply-2"


@respx.mock
async def test_confirm_order_unreadable_response_reports_possible_placement(mcp_client):
    respx.post(f"{BASE_URL}/iserver/reply/reply-1").mock(
        return_value=httpx.Response(200, json={"error": "unexpected shape"})
    )

    async with mcp_client:
        with pytest.raises(ToolError) as exc_info:
            await mcp_client.call_tool(
                name="confirmOrder",
                arguments={"reply_id": "reply-1"},
            )

    assert "may already be placed" in str(exc_info.value)


async def test_order_tools_registered_by_default(mcp_client):
    async with mcp_client:
        tool_names = {tool.name for tool in await mcp_client.list_tools()}

    assert {"placeOrder", "confirmOrder"} <= tool_names


async def test_order_tools_hidden_when_read_only(monkeypatch):
    monkeypatch.setattr("config.settings.read_only", True)
    read_only_app = importlib.reload(mcp_app.app)

    try:
        async with Client(read_only_app.mcp_app) as client:
            tool_names = {tool.name for tool in await client.list_tools()}
    finally:
        monkeypatch.undo()
        importlib.reload(mcp_app.app)

    assert "placeOrder" not in tool_names
    assert "confirmOrder" not in tool_names
    assert "getAccounts" in tool_names
