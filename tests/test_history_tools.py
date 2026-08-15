import json

import httpx
import pytest
import respx
from fastmcp import Client
from fastmcp.exceptions import ToolError

import mcp_app.app
from interactive_brokers.ib_client import InteractiveBrokersClient
from interactive_brokers.models import TransactionHistoryRequest
from tests.conftest import BASE_URL

ACCOUNT_ID = "DU1234567"
CONTRACT_ID = 265598
TRADES_URL = f"{BASE_URL}/iserver/account/trades"
TRANSACTIONS_URL = f"{BASE_URL}/pa/transactions"

TRADES_PAYLOAD = [
    {
        "execution_id": "0000e0d5.64f3a1b2.01.01",
        "symbol": "AAPL",
        "side": "B",
        "order_description": "Bot 10 AAPL @ 231.44 on ISLAND",
        "order_type": "MARKET",
        "trade_time": "20260814-16:53:21",
        "trade_time_r": 1755190401000,
        "size": 10.0,
        "price": "231.44",
        "commission": "1.00",
        "net_amount": 2314.4,
        "exchange": "ISLAND",
        "order_ref": "deadbeefcafe",
        "account": ACCOUNT_ID,
        "accountCode": ACCOUNT_ID,
        "company_name": "APPLE INC",
        "sec_type": "STK",
        "conid": "265598",
    },
    {
        "execution_id": "0000e0d5.64f3a1b2.01.02",
        "symbol": "MSFT",
        "side": "S",
        "trade_time": "20260813-14:02:07",
        "size": 5.0,
        "price": "410.50",
        # IB sends an empty string rather than null for a figure it lacks.
        "commission": "",
        "net_amount": 2052.5,
        "account": ACCOUNT_ID,
        "sec_type": "STK",
        "conid": "272093",
    },
]

TRANSACTIONS_PAYLOAD = {
    "id": "getTransactions",
    "currency": "USD",
    "from": 1747180800000,
    "to": 1755190401000,
    "includesRealTime": True,
    "transactions": [
        {
            "date": "Thu Aug 14 00:00:00 EDT 2026",
            "cur": "USD",
            "pr": 231.44,
            "qty": 10.0,
            "amt": -2314.4,
            "conid": CONTRACT_ID,
            "desc": "APPLE INC",
            "type": "Buy",
            "acctid": ACCOUNT_ID,
            "fxRateToBase": 1,
        },
        {
            "date": "Mon Jul 20 00:00:00 EDT 2026",
            "cur": "USD",
            "qty": 0.0,
            "amt": 24.0,
            "conid": CONTRACT_ID,
            "desc": "APPLE INC CASH DIVIDEND",
            "type": "Dividend",
            "acctid": ACCOUNT_ID,
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
async def test_get_trades_parses_response(ib_client):
    respx.get(TRADES_URL).mock(return_value=httpx.Response(200, json=TRADES_PAYLOAD))

    results = await ib_client.get_trades()

    assert len(results) == 2
    assert results[0].execution_id == "0000e0d5.64f3a1b2.01.01"
    # IB sends the price and commission as strings and the conid as a string.
    assert results[0].price == 231.44
    assert results[0].commission == 1.0
    assert results[0].conid == 265598
    assert results[1].commission is None


@respx.mock
async def test_get_trades_forwards_query_params(ib_client):
    route = respx.get(TRADES_URL).mock(
        return_value=httpx.Response(200, json=TRADES_PAYLOAD)
    )

    await ib_client.get_trades(account_id=ACCOUNT_ID, days=7)

    params = route.calls.last.request.url.params
    assert params["accountId"] == ACCOUNT_ID
    assert params["days"] == "7"


@respx.mock
async def test_get_trades_omits_unset_query_params(ib_client):
    route = respx.get(TRADES_URL).mock(
        return_value=httpx.Response(200, json=TRADES_PAYLOAD)
    )

    await ib_client.get_trades()

    params = route.calls.last.request.url.params
    assert "accountId" not in params
    assert "days" not in params


@respx.mock
async def test_get_trades_raises_on_http_error(ib_client):
    respx.get(TRADES_URL).mock(return_value=httpx.Response(500, text="boom"))

    with pytest.raises(httpx.HTTPStatusError):
        await ib_client.get_trades()


@respx.mock
async def test_get_transaction_history_sends_ib_envelope(ib_client):
    route = respx.post(TRANSACTIONS_URL).mock(
        return_value=httpx.Response(200, json=TRANSACTIONS_PAYLOAD)
    )

    await ib_client.get_transaction_history(
        TransactionHistoryRequest(
            acct_ids=[ACCOUNT_ID],
            conids=[CONTRACT_ID],
            currency="EUR",
            days="30",
        )
    )

    payload = json.loads(route.calls.last.request.content)
    assert payload == {
        "acctIds": [ACCOUNT_ID],
        "conids": [CONTRACT_ID],
        "currency": "EUR",
        "days": "30",
    }


@respx.mock
async def test_get_transaction_history_unwraps_envelope(ib_client):
    respx.post(TRANSACTIONS_URL).mock(
        return_value=httpx.Response(200, json=TRANSACTIONS_PAYLOAD)
    )

    results = await ib_client.get_transaction_history(
        TransactionHistoryRequest(acct_ids=[ACCOUNT_ID], conids=[CONTRACT_ID])
    )

    assert len(results) == 2
    assert results[0].amount == -2314.4
    assert results[0].type == "Buy"
    assert results[1].type == "Dividend"
    assert results[1].price is None


@respx.mock
async def test_get_transaction_history_handles_missing_key(ib_client):
    respx.post(TRANSACTIONS_URL).mock(
        return_value=httpx.Response(200, json={"id": "getTransactions"})
    )

    results = await ib_client.get_transaction_history(
        TransactionHistoryRequest(acct_ids=[ACCOUNT_ID], conids=[CONTRACT_ID])
    )

    assert results == []


@respx.mock
async def test_trades_tool_maps_fields(mcp_client):
    respx.get(TRADES_URL).mock(return_value=httpx.Response(200, json=TRADES_PAYLOAD))

    async with mcp_client:
        result = await mcp_client.call_tool(name="getTrades", arguments={"days": 7})

    trades = result.structured_content["result"]
    assert len(trades) == 2

    bought = trades[0]
    assert bought["execution_id"] == "0000e0d5.64f3a1b2.01.01"
    assert bought["client_order_id"] == "deadbeefcafe"
    assert bought["account_id"] == ACCOUNT_ID
    # "B" must normalise to the same enum the order tools report.
    assert bought["side"] == "BUY"
    assert bought["symbol"] == "AAPL"
    assert bought["contract_id"] == 265598
    assert bought["quantity"] == 10.0
    assert bought["price"] == 231.44
    assert bought["commission"] == 1.0
    assert bought["net_amount"] == 2314.4

    sold = trades[1]
    assert sold["side"] == "SELL"
    assert sold["commission"] is None
    assert sold["client_order_id"] is None


@respx.mock
async def test_trades_tool_rejects_window_beyond_ib_limit(mcp_client):
    async with mcp_client:
        with pytest.raises(ToolError, match="between 1 and 7"):
            await mcp_client.call_tool(name="getTrades", arguments={"days": 30})


@respx.mock
async def test_trades_tool_rejects_zero_days(mcp_client):
    async with mcp_client:
        with pytest.raises(ToolError, match="between 1 and 7"):
            await mcp_client.call_tool(name="getTrades", arguments={"days": 0})


@respx.mock
async def test_trades_tool_accepts_the_boundary(mcp_client):
    route = respx.get(TRADES_URL).mock(
        return_value=httpx.Response(200, json=TRADES_PAYLOAD)
    )

    async with mcp_client:
        await mcp_client.call_tool(name="getTrades", arguments={"days": 7})

    assert route.calls.last.request.url.params["days"] == "7"


@respx.mock
async def test_transaction_history_tool_maps_fields(mcp_client):
    route = respx.post(TRANSACTIONS_URL).mock(
        return_value=httpx.Response(200, json=TRANSACTIONS_PAYLOAD)
    )

    async with mcp_client:
        result = await mcp_client.call_tool(
            name="getTransactionHistory",
            arguments={"account_id": ACCOUNT_ID, "contract_id": CONTRACT_ID},
        )

    # days defaults to IB's own 90 day window.
    assert json.loads(route.calls.last.request.content)["days"] == "90"

    transactions = result.structured_content["result"]
    assert len(transactions) == 2

    bought = transactions[0]
    assert bought["type"] == "Buy"
    assert bought["quantity"] == 10.0
    assert bought["price"] == 231.44
    assert bought["amount"] == -2314.4
    assert bought["currency"] == "USD"
    assert bought["contract_id"] == CONTRACT_ID
    assert bought["account_id"] == ACCOUNT_ID
    assert bought["fx_rate_to_base"] == 1.0

    # A dividend has no counterpart in getTrades, which covers executions only.
    dividend = transactions[1]
    assert dividend["type"] == "Dividend"
    assert dividend["amount"] == 24.0
    assert dividend["price"] is None


@respx.mock
async def test_transaction_history_tool_rejects_zero_days(mcp_client):
    async with mcp_client:
        with pytest.raises(ToolError, match="days must be 1 or greater"):
            await mcp_client.call_tool(
                name="getTransactionHistory",
                arguments={
                    "account_id": ACCOUNT_ID,
                    "contract_id": CONTRACT_ID,
                    "days": 0,
                },
            )
