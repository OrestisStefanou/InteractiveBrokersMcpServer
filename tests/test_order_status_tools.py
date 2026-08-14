import httpx
import pytest
import respx
from fastmcp import Client

import mcp_app.app
from interactive_brokers.ib_client import InteractiveBrokersClient
from tests.conftest import BASE_URL

ACCOUNT_ID = "DU1234567"
ORDER_ID = "1234567"
STATUS_URL = f"{BASE_URL}/iserver/account/order/status/{ORDER_ID}"
LIVE_ORDERS_URL = f"{BASE_URL}/iserver/account/orders"

STATUS_PAYLOAD = {
    "order_id": 1234567,
    "account": ACCOUNT_ID,
    "conid": 265598,
    "symbol": "AAPL",
    "company_name": "APPLE INC",
    "sec_type": "STK",
    "listing_exchange": "NASDAQ.NMS",
    "currency": "USD",
    "side": "B",
    "order_type": "MARKET",
    "order_status": "Filled",
    "order_status_description": "Order Filled",
    "order_ccp_status": "2",
    "total_size": "10.0",
    "size": "0.0",
    "cum_fill": "10.0",
    "average_price": "231.44",
    "tif": "DAY",
    "outside_rth": False,
    "order_time": "220830165321",
    "order_description": "Bought 10 Market, Day",
    "order_description_with_contract": "Bought 10 AAPL Market, Day",
    "cannot_cancel_order": True,
    "order_not_editable": True,
    "sub_type": None,
}

LIVE_ORDERS_PAYLOAD = {
    "snapshot": True,
    "orders": [
        {
            "acct": ACCOUNT_ID,
            "orderId": 1234567,
            "conid": 265598,
            "ticker": "AAPL",
            "companyName": "APPLE INC",
            "secType": "STK",
            "listingExchange": "NASDAQ.NMS",
            "cashCcy": "USD",
            "side": "BUY",
            "status": "Filled",
            "orderType": "Market",
            "origOrderType": "MARKET",
            "totalSize": 10,
            "filledQuantity": 10,
            "remainingQuantity": 0,
            "avgPrice": "231.44",
            "timeInForce": "DAY",
            "order_ref": "deadbeefcafe",
            "orderDesc": "Bought 10 Market, Day",
            "sizeAndFills": "10",
            "lastExecutionTime": "220830165321",
            "lastExecutionTime_r": 1661874801000,
        },
        {
            "acct": ACCOUNT_ID,
            "orderId": 7654321,
            "conid": 272093,
            "ticker": "MSFT",
            "side": "SELL",
            "status": "Submitted",
            "orderType": "Limit",
            "totalSize": 5,
            "filledQuantity": 0,
            "remainingQuantity": 5,
            # IB sends an empty string rather than null for an unfilled average.
            "avgPrice": "",
            "price": 410.5,
            "timeInForce": "GTC",
        },
    ],
}


@pytest.fixture
def ib_client() -> InteractiveBrokersClient:
    return InteractiveBrokersClient(base_url=BASE_URL)


@pytest.fixture
def mcp_client() -> Client:
    return Client(mcp_app.app.mcp_app)


@respx.mock
async def test_get_order_status_parses_response(ib_client):
    respx.get(STATUS_URL).mock(return_value=httpx.Response(200, json=STATUS_PAYLOAD))

    result = await ib_client.get_order_status(ORDER_ID)

    assert result.order_id == 1234567
    assert result.order_status == "Filled"
    # IB sends the quantities as strings on this endpoint.
    assert result.total_size == 10.0
    assert result.cum_fill == 10.0
    assert result.average_price == 231.44


@respx.mock
async def test_get_order_status_treats_blank_numbers_as_missing(ib_client):
    respx.get(STATUS_URL).mock(
        return_value=httpx.Response(
            200,
            json={**STATUS_PAYLOAD, "average_price": "", "cum_fill": ""},
        )
    )

    result = await ib_client.get_order_status(ORDER_ID)

    assert result.average_price is None
    assert result.cum_fill is None


@respx.mock
async def test_get_order_status_raises_on_http_error(ib_client):
    respx.get(STATUS_URL).mock(return_value=httpx.Response(500, text="boom"))

    with pytest.raises(httpx.HTTPStatusError):
        await ib_client.get_order_status(ORDER_ID)


@respx.mock
async def test_get_live_orders_unwraps_envelope(ib_client):
    respx.get(LIVE_ORDERS_URL).mock(
        return_value=httpx.Response(200, json=LIVE_ORDERS_PAYLOAD)
    )

    results = await ib_client.get_live_orders()

    assert len(results) == 2
    assert results[0].order_id == 1234567
    assert results[0].order_ref == "deadbeefcafe"
    assert results[1].avg_price is None


@respx.mock
async def test_get_live_orders_handles_missing_orders_key(ib_client):
    respx.get(LIVE_ORDERS_URL).mock(
        return_value=httpx.Response(200, json={"snapshot": False})
    )

    assert await ib_client.get_live_orders() == []


@respx.mock
async def test_get_live_orders_handles_null_orders(ib_client):
    respx.get(LIVE_ORDERS_URL).mock(
        return_value=httpx.Response(200, json={"snapshot": False, "orders": None})
    )

    assert await ib_client.get_live_orders() == []


@respx.mock
async def test_get_live_orders_forwards_account_filter(ib_client):
    route = respx.get(LIVE_ORDERS_URL).mock(
        return_value=httpx.Response(200, json=LIVE_ORDERS_PAYLOAD)
    )

    await ib_client.get_live_orders(account_id=ACCOUNT_ID)

    assert route.calls.last.request.url.params["accountId"] == ACCOUNT_ID


@respx.mock
async def test_get_live_orders_omits_account_filter_when_unset(ib_client):
    route = respx.get(LIVE_ORDERS_URL).mock(
        return_value=httpx.Response(200, json=LIVE_ORDERS_PAYLOAD)
    )

    await ib_client.get_live_orders()

    assert "accountId" not in route.calls.last.request.url.params


@respx.mock
async def test_order_status_tool_maps_fields(mcp_client):
    respx.get(STATUS_URL).mock(return_value=httpx.Response(200, json=STATUS_PAYLOAD))

    async with mcp_client:
        result = await mcp_client.call_tool(
            name="getOrderStatus", arguments={"order_id": ORDER_ID}
        )

    status = result.structured_content
    assert status["order_id"] == 1234567
    assert status["status"] == "Filled"
    assert status["status_description"] == "Order Filled"
    # "B" must be normalised to the same enum live orders report as "BUY".
    assert status["side"] == "BUY"
    assert status["symbol"] == "AAPL"
    assert status["contract_id"] == 265598
    assert status["total_quantity"] == 10.0
    assert status["filled_quantity"] == 10.0
    assert status["remaining_quantity"] == 0.0
    assert status["average_price"] == 231.44
    assert status["time_in_force"] == "DAY"
    assert status["cannot_cancel"] is True
    assert status["description"] == "Bought 10 AAPL Market, Day"


@respx.mock
async def test_order_status_tool_normalises_sell_side(mcp_client):
    respx.get(STATUS_URL).mock(
        return_value=httpx.Response(200, json={**STATUS_PAYLOAD, "side": "S"})
    )

    async with mcp_client:
        result = await mcp_client.call_tool(
            name="getOrderStatus", arguments={"order_id": ORDER_ID}
        )

    assert result.structured_content["side"] == "SELL"


@respx.mock
async def test_order_status_tool_leaves_remaining_null_when_underivable(mcp_client):
    respx.get(STATUS_URL).mock(
        return_value=httpx.Response(200, json={**STATUS_PAYLOAD, "cum_fill": ""})
    )

    async with mcp_client:
        result = await mcp_client.call_tool(
            name="getOrderStatus", arguments={"order_id": ORDER_ID}
        )

    status = result.structured_content
    assert status["filled_quantity"] is None
    assert status["remaining_quantity"] is None


@respx.mock
async def test_order_status_tool_reports_partial_fill(mcp_client):
    respx.get(STATUS_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                **STATUS_PAYLOAD,
                "order_status": "Submitted",
                "cum_fill": "4.0",
                "average_price": "231.10",
            },
        )
    )

    async with mcp_client:
        result = await mcp_client.call_tool(
            name="getOrderStatus", arguments={"order_id": ORDER_ID}
        )

    status = result.structured_content
    assert status["status"] == "Submitted"
    assert status["filled_quantity"] == 4.0
    assert status["remaining_quantity"] == 6.0


@respx.mock
async def test_live_orders_tool_exposes_client_order_id(mcp_client):
    respx.get(LIVE_ORDERS_URL).mock(
        return_value=httpx.Response(200, json=LIVE_ORDERS_PAYLOAD)
    )

    async with mcp_client:
        result = await mcp_client.call_tool(
            name="getLiveOrders", arguments={"account_id": ACCOUNT_ID}
        )

    orders = result.structured_content["result"]
    assert len(orders) == 2

    filled = orders[0]
    assert filled["order_id"] == 1234567
    # The reconciliation path in placeOrder depends on this being surfaced.
    assert filled["client_order_id"] == "deadbeefcafe"
    assert filled["account_id"] == ACCOUNT_ID
    assert filled["status"] == "Filled"
    assert filled["side"] == "BUY"
    assert filled["ticker"] == "AAPL"
    assert filled["filled_quantity"] == 10.0
    assert filled["remaining_quantity"] == 0.0
    assert filled["average_price"] == 231.44

    working = orders[1]
    assert working["status"] == "Submitted"
    assert working["side"] == "SELL"
    assert working["average_price"] is None
    assert working["limit_price"] == 410.5
    assert working["client_order_id"] is None


@respx.mock
async def test_live_orders_tool_returns_empty_list_when_not_ready(mcp_client):
    respx.get(LIVE_ORDERS_URL).mock(
        return_value=httpx.Response(200, json={"snapshot": False})
    )

    async with mcp_client:
        result = await mcp_client.call_tool(name="getLiveOrders", arguments={})

    assert result.structured_content["result"] == []
