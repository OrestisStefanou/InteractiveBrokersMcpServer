import httpx
import pytest
import respx
from fastmcp import Client
from fastmcp.exceptions import ToolError

import mcp_app.app
from interactive_brokers.errors import OrderResponseParseError
from interactive_brokers.ib_client import InteractiveBrokersClient
from tests.conftest import BASE_URL

ACCOUNT_ID = "DU1234567"
ORDER_ID = "1234567"
CANCEL_URL = f"{BASE_URL}/iserver/account/{ACCOUNT_ID}/order/{ORDER_ID}"

CANCEL_ARGS = {"account_id": ACCOUNT_ID, "order_id": ORDER_ID}

CANCEL_PAYLOAD = {
    "order_id": 1234567,
    "msg": "Request was submitted",
    "conid": 265598,
    "account": ACCOUNT_ID,
}


@pytest.fixture
def ib_client() -> InteractiveBrokersClient:
    return InteractiveBrokersClient(base_url=BASE_URL)


@pytest.fixture
def mcp_client() -> Client:
    return Client(mcp_app.app.mcp_app)


@respx.mock
async def test_cancel_order_issues_delete(ib_client):
    route = respx.delete(CANCEL_URL).mock(
        return_value=httpx.Response(200, json=CANCEL_PAYLOAD)
    )

    result = await ib_client.cancel_order(account_id=ACCOUNT_ID, order_id=ORDER_ID)

    assert route.calls.last.request.method == "DELETE"
    assert result.order_id == 1234567
    assert result.msg == "Request was submitted"


@respx.mock
async def test_cancel_order_parses_reject(ib_client):
    respx.delete(CANCEL_URL).mock(
        return_value=httpx.Response(200, json={"error": "Order already filled"})
    )

    result = await ib_client.cancel_order(account_id=ACCOUNT_ID, order_id=ORDER_ID)

    assert result.error == "Order already filled"


@respx.mock
async def test_cancel_order_raises_parse_error_with_payload(ib_client):
    payload = [{"unexpected": "shape"}]
    respx.delete(CANCEL_URL).mock(return_value=httpx.Response(200, json=payload))

    with pytest.raises(OrderResponseParseError) as exc_info:
        await ib_client.cancel_order(account_id=ACCOUNT_ID, order_id=ORDER_ID)

    assert exc_info.value.payload == payload


@respx.mock
async def test_cancel_order_raises_on_http_error(ib_client):
    respx.delete(CANCEL_URL).mock(return_value=httpx.Response(500, text="boom"))

    with pytest.raises(httpx.HTTPStatusError):
        await ib_client.cancel_order(account_id=ACCOUNT_ID, order_id=ORDER_ID)


@respx.mock
async def test_cancel_tool_reports_submitted(mcp_client):
    respx.delete(CANCEL_URL).mock(
        return_value=httpx.Response(200, json=CANCEL_PAYLOAD)
    )

    async with mcp_client:
        result = await mcp_client.call_tool(name="cancelOrder", arguments=CANCEL_ARGS)

    cancellation = result.structured_content
    assert cancellation["submitted"] is True
    assert cancellation["order_id"] == ORDER_ID
    assert cancellation["account_id"] == ACCOUNT_ID
    assert cancellation["contract_id"] == 265598
    assert cancellation["message"] == "Request was submitted"
    assert cancellation["error"] is None


@respx.mock
async def test_cancel_tool_reports_refusal(mcp_client):
    respx.delete(CANCEL_URL).mock(
        return_value=httpx.Response(200, json={"error": "Order already filled"})
    )

    async with mcp_client:
        result = await mcp_client.call_tool(name="cancelOrder", arguments=CANCEL_ARGS)

    cancellation = result.structured_content
    assert cancellation["submitted"] is False
    assert cancellation["error"] == "Order already filled"
    # The echoed arguments must survive a response that carries neither.
    assert cancellation["order_id"] == ORDER_ID
    assert cancellation["account_id"] == ACCOUNT_ID


@respx.mock
async def test_cancel_tool_surfaces_unreadable_response(mcp_client):
    respx.delete(CANCEL_URL).mock(
        return_value=httpx.Response(200, json=[{"unexpected": "shape"}])
    )

    async with mcp_client:
        with pytest.raises(ToolError, match="may or may not still be working"):
            await mcp_client.call_tool(name="cancelOrder", arguments=CANCEL_ARGS)


async def test_cancel_tool_is_hidden_in_read_only_mode(monkeypatch):
    import importlib

    from config import settings

    monkeypatch.setattr(settings, "read_only", True)
    read_only_app = importlib.reload(mcp_app.app)

    try:
        async with Client(read_only_app.mcp_app) as client:
            names = {tool.name for tool in await client.list_tools()}

        assert "cancelOrder" not in names
        assert "placeOrder" not in names
        # Read tools stay available.
        assert "getQuotes" in names
        assert "getOrderStatus" in names
    finally:
        monkeypatch.setattr(settings, "read_only", False)
        importlib.reload(mcp_app.app)
