import httpx
import pytest
import respx
from fastmcp import Client

import mcp_app.app
from interactive_brokers.ib_client import InteractiveBrokersClient
from tests.conftest import BASE_URL

ACCOUNT_ID = "DU1234567"
SUMMARY_URL = f"{BASE_URL}/portfolio/{ACCOUNT_ID}/summary"
LEDGER_URL = f"{BASE_URL}/portfolio/{ACCOUNT_ID}/ledger"


def summary_value(amount: float, currency: str = "USD", **overrides) -> dict:
    value = {
        "amount": amount,
        "currency": currency,
        "isNull": False,
        "severity": 0,
        "timestamp": 1723600000000,
        "value": "",
    }
    value.update(overrides)
    return value


SUMMARY_PAYLOAD = {
    "netliquidation": summary_value(100000.0),
    "totalcashvalue": summary_value(98500.0),
    "settledcash": summary_value(98500.0),
    "accruedcash": summary_value(12.5),
    "buyingpower": summary_value(394000.0),
    "availablefunds": summary_value(98500.0),
    "excessliquidity": summary_value(97000.0),
    "equitywithloanvalue": summary_value(99000.0),
    "grosspositionvalue": summary_value(1500.0),
    "initmarginreq": summary_value(750.0),
    "maintmarginreq": summary_value(500.0),
    "cushion": summary_value(0.97, currency=""),
    "unrealizedpnl": summary_value(150.0),
    "realizedpnl": summary_value(-20.0),
    "daytradesremaining": summary_value(-1.0, currency=""),
    "accounttype": summary_value(0.0, currency="", value="DEMO"),
    # Segment-specific duplicates IB also returns; must not confuse the mapping.
    "availablefunds-c": summary_value(0.0),
    "availablefunds-s": summary_value(98500.0),
}

LEDGER_PAYLOAD = {
    "BASE": {
        "cashbalance": 98500.0,
        "settledcash": 98500.0,
        "netliquidationvalue": 100000.0,
        "stockmarketvalue": 1500.0,
        "exchangerate": 1.0,
        "unrealizedpnl": 150.0,
        "realizedpnl": -20.0,
        "interest": 3.5,
        "dividends": 0.0,
        "currency": "BASE",
        "secondkey": "USD",
        "acctcode": ACCOUNT_ID,
        "timestamp": 1723600000,
    },
    "EUR": {
        "cashbalance": 44000.0,
        "settledcash": 44000.0,
        "netliquidationvalue": 44000.0,
        "exchangerate": 1.1,
        "currency": "EUR",
        "acctcode": ACCOUNT_ID,
    },
}


@pytest.fixture
def ib_client() -> InteractiveBrokersClient:
    return InteractiveBrokersClient(base_url=BASE_URL)


@pytest.fixture
def mcp_client() -> Client:
    return Client(mcp_app.app.mcp_app)


@respx.mock
async def test_get_account_summary_parses_values(ib_client):
    respx.get(SUMMARY_URL).mock(return_value=httpx.Response(200, json=SUMMARY_PAYLOAD))

    result = await ib_client.get_account_summary(ACCOUNT_ID)

    assert result.net_liquidation.amount == 100000.0
    assert result.net_liquidation.currency == "USD"
    assert result.buying_power.amount == 394000.0
    assert result.account_type.value == "DEMO"


@respx.mock
async def test_get_account_ledger_keys_entries_by_currency(ib_client):
    respx.get(LEDGER_URL).mock(return_value=httpx.Response(200, json=LEDGER_PAYLOAD))

    results = await ib_client.get_account_ledger(ACCOUNT_ID)

    by_currency = {entry.currency: entry for entry in results}
    assert set(by_currency) == {"BASE", "EUR"}
    assert by_currency["BASE"].cash_balance == 98500.0
    assert by_currency["BASE"].net_liquidation_value == 100000.0
    assert by_currency["EUR"].exchange_rate == 1.1


@respx.mock
async def test_get_account_ledger_skips_non_object_entries(ib_client):
    respx.get(LEDGER_URL).mock(
        return_value=httpx.Response(
            200, json={**LEDGER_PAYLOAD, "endofbundle": 1, "acctcode": ACCOUNT_ID}
        )
    )

    results = await ib_client.get_account_ledger(ACCOUNT_ID)

    assert {entry.currency for entry in results} == {"BASE", "EUR"}


@respx.mock
async def test_get_account_summary_raises_on_http_error(ib_client):
    respx.get(SUMMARY_URL).mock(return_value=httpx.Response(500, text="boom"))

    with pytest.raises(httpx.HTTPStatusError):
        await ib_client.get_account_summary(ACCOUNT_ID)


@respx.mock
async def test_summary_tool_flattens_amounts(mcp_client):
    respx.get(SUMMARY_URL).mock(return_value=httpx.Response(200, json=SUMMARY_PAYLOAD))

    async with mcp_client:
        result = await mcp_client.call_tool(
            name="getAccountSummary", arguments={"account_id": ACCOUNT_ID}
        )

    summary = result.structured_content
    assert summary["currency"] == "USD"
    assert summary["net_liquidation"] == 100000.0
    assert summary["total_cash_value"] == 98500.0
    assert summary["buying_power"] == 394000.0
    assert summary["available_funds"] == 98500.0
    assert summary["excess_liquidity"] == 97000.0
    assert summary["initial_margin_requirement"] == 750.0
    assert summary["maintenance_margin_requirement"] == 500.0
    assert summary["cushion"] == 0.97
    assert summary["unrealized_pnl"] == 150.0
    assert summary["realized_pnl"] == -20.0
    assert summary["day_trades_remaining"] == -1.0
    assert summary["account_type"] == "DEMO"


@respx.mock
async def test_summary_tool_reports_null_fields_as_none(mcp_client):
    respx.get(SUMMARY_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                **SUMMARY_PAYLOAD,
                # IB flags an unavailable field as isNull with an amount of 0;
                # surfacing that 0 would read as a real zero balance.
                "buyingpower": summary_value(0.0, isNull=True),
            },
        )
    )

    async with mcp_client:
        result = await mcp_client.call_tool(
            name="getAccountSummary", arguments={"account_id": ACCOUNT_ID}
        )

    assert result.structured_content["buying_power"] is None


@respx.mock
async def test_summary_tool_handles_missing_fields(mcp_client):
    respx.get(SUMMARY_URL).mock(
        return_value=httpx.Response(200, json={"netliquidation": summary_value(50.0)})
    )

    async with mcp_client:
        result = await mcp_client.call_tool(
            name="getAccountSummary", arguments={"account_id": ACCOUNT_ID}
        )

    summary = result.structured_content
    assert summary["net_liquidation"] == 50.0
    assert summary["currency"] == "USD"
    assert summary["buying_power"] is None
    assert summary["account_type"] is None


@respx.mock
async def test_balances_tool_returns_one_entry_per_currency(mcp_client):
    respx.get(LEDGER_URL).mock(return_value=httpx.Response(200, json=LEDGER_PAYLOAD))

    async with mcp_client:
        result = await mcp_client.call_tool(
            name="getAccountBalances", arguments={"account_id": ACCOUNT_ID}
        )

    balances = {entry["currency"]: entry for entry in result.structured_content["result"]}
    assert set(balances) == {"BASE", "EUR"}
    assert balances["BASE"]["cash_balance"] == 98500.0
    assert balances["BASE"]["settled_cash"] == 98500.0
    assert balances["BASE"]["stock_market_value"] == 1500.0
    assert balances["BASE"]["interest"] == 3.5
    assert balances["EUR"]["cash_balance"] == 44000.0
    assert balances["EUR"]["exchange_rate"] == 1.1
    assert balances["EUR"]["stock_market_value"] is None
