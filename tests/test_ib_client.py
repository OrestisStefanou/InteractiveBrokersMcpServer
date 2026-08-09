import json

import httpx
import pytest
import respx

from interactive_brokers.errors import OrderResponseParseError
from interactive_brokers.ib_client import InteractiveBrokersClient
from interactive_brokers.models import (
    OrderSide,
    OrderType,
    PlaceOrderRequest,
    TimeInForce,
)
from tests.conftest import BASE_URL

ACCOUNT_ID = "DU1234567"
ORDERS_URL = f"{BASE_URL}/iserver/account/{ACCOUNT_ID}/orders"


def market_order(**overrides) -> PlaceOrderRequest:
    kwargs = {
        "conid": 265598,
        "order_type": OrderType.MARKET,
        "side": OrderSide.BUY,
        "quantity": 1,
        "c_oid": "abc123",
        "tif": TimeInForce.DAY,
        "acct_id": ACCOUNT_ID,
    }
    kwargs.update(overrides)
    return PlaceOrderRequest(**kwargs)


@pytest.fixture
def ib_client() -> InteractiveBrokersClient:
    return InteractiveBrokersClient(base_url=BASE_URL)


@respx.mock
async def test_place_order_sends_ib_order_envelope(ib_client):
    route = respx.post(ORDERS_URL).mock(
        return_value=httpx.Response(200, json=[{"order_id": "1", "order_status": "PreSubmitted"}])
    )

    await ib_client.place_order(account_id=ACCOUNT_ID, order=market_order())

    payload = json.loads(route.calls.last.request.content)
    assert list(payload) == ["orders"]
    assert len(payload["orders"]) == 1

    order = payload["orders"][0]
    assert order["conid"] == 265598
    assert order["orderType"] == "MKT"
    assert order["side"] == "BUY"
    assert order["quantity"] == 1
    assert order["c_oid"] == "abc123"
    assert order["tif"] == "DAY"
    assert order["acctId"] == ACCOUNT_ID
    # exclude_none must keep price out of a market order entirely.
    assert "price" not in order


@respx.mock
async def test_place_order_parses_confirmation(ib_client):
    respx.post(ORDERS_URL).mock(
        return_value=httpx.Response(
            200, json=[{"order_id": "1234", "order_status": "PreSubmitted"}]
        )
    )

    results = await ib_client.place_order(account_id=ACCOUNT_ID, order=market_order())

    assert len(results) == 1
    assert results[0].order_id == "1234"
    assert results[0].order_status == "PreSubmitted"
    assert results[0].id is None


@respx.mock
async def test_place_order_parses_warning(ib_client):
    respx.post(ORDERS_URL).mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "id": "reply-1",
                    "message": ["Your order size is above the typical size."],
                    "isSuppressed": False,
                    "messageIds": ["o163"],
                }
            ],
        )
    )

    results = await ib_client.place_order(account_id=ACCOUNT_ID, order=market_order())

    assert results[0].id == "reply-1"
    assert results[0].message == ["Your order size is above the typical size."]
    assert results[0].is_suppressed is False
    assert results[0].message_ids == ["o163"]


@respx.mock
async def test_place_order_parses_reject(ib_client):
    respx.post(ORDERS_URL).mock(
        return_value=httpx.Response(200, json=[{"error": "Contract is not tradable"}])
    )

    results = await ib_client.place_order(account_id=ACCOUNT_ID, order=market_order())

    assert results[0].error == "Contract is not tradable"


@respx.mock
async def test_place_order_raises_parse_error_with_payload(ib_client):
    payload = {"error": "unexpected shape"}
    respx.post(ORDERS_URL).mock(return_value=httpx.Response(200, json=payload))

    with pytest.raises(OrderResponseParseError) as exc_info:
        await ib_client.place_order(account_id=ACCOUNT_ID, order=market_order())

    assert exc_info.value.payload == payload


@respx.mock
async def test_place_order_raises_on_http_error(ib_client):
    respx.post(ORDERS_URL).mock(return_value=httpx.Response(500, text="boom"))

    with pytest.raises(httpx.HTTPStatusError):
        await ib_client.place_order(account_id=ACCOUNT_ID, order=market_order())


@respx.mock
async def test_confirm_order_posts_reply(ib_client):
    route = respx.post(f"{BASE_URL}/iserver/reply/reply-1").mock(
        return_value=httpx.Response(
            200, json=[{"order_id": "1234", "order_status": "Submitted"}]
        )
    )

    results = await ib_client.confirm_order(reply_id="reply-1")

    assert json.loads(route.calls.last.request.content) == {"confirmed": True}
    assert results[0].order_id == "1234"
    assert results[0].order_status == "Submitted"


@respx.mock
async def test_confirm_order_can_decline(ib_client):
    route = respx.post(f"{BASE_URL}/iserver/reply/reply-1").mock(
        return_value=httpx.Response(200, json=[{"order_id": "1234"}])
    )

    await ib_client.confirm_order(reply_id="reply-1", confirmed=False)

    assert json.loads(route.calls.last.request.content) == {"confirmed": False}


@respx.mock
async def test_confirm_order_can_return_further_warning(ib_client):
    respx.post(f"{BASE_URL}/iserver/reply/reply-1").mock(
        return_value=httpx.Response(
            200, json=[{"id": "reply-2", "message": ["Are you sure?"]}]
        )
    )

    results = await ib_client.confirm_order(reply_id="reply-1")

    assert results[0].id == "reply-2"


@respx.mock
async def test_confirm_order_raises_parse_error_with_payload(ib_client):
    payload = {"error": "unexpected shape"}
    respx.post(f"{BASE_URL}/iserver/reply/reply-1").mock(
        return_value=httpx.Response(200, json=payload)
    )

    with pytest.raises(OrderResponseParseError) as exc_info:
        await ib_client.confirm_order(reply_id="reply-1")

    assert exc_info.value.payload == payload


def test_limit_order_requires_price():
    with pytest.raises(ValueError, match="price is required for LIMIT orders"):
        market_order(order_type=OrderType.LIMIT)
