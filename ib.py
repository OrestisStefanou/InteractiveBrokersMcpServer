"""
IBKR Client Portal Web API – Python Client
==========================================
Prerequisites:
  1. IBKR Pro account (live or paper)
  2. Client Portal Gateway running and authenticated (see README below)
  3. pip install httpx

Usage:
  python ibkr_client.py

The gateway runs at https://localhost:5000 and uses a self-signed TLS cert.
verify=False is set once on the shared Client instance – httpx does not emit
urllib3-style SSL warnings, so no extra suppression is needed.
"""

import json
import time

import httpx

BASE_URL = "https://localhost:5000/v1/api"

# ── Shared client – verify=False handles the Gateway's self-signed cert ───────
# httpx.Client reuses the connection pool across calls and never emits
# urllib3-style SSL warnings, so no extra suppression is needed.
_client = httpx.Client(base_url=BASE_URL, verify=False)


# ─────────────────────────────────────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────────────────────────────────────


def _get(path: str, params: dict = None) -> dict | list:
    """GET request against the Gateway."""
    r = _client.get(path, params=params)
    r.raise_for_status()
    return r.json()


def _post(path: str, payload: dict = None) -> dict | list:
    """POST request against the Gateway."""
    r = _client.post(path, json=payload)
    r.raise_for_status()
    return r.json()


def _delete(path: str) -> dict | list:
    """DELETE request against the Gateway."""
    r = _client.delete(path)
    r.raise_for_status()
    return r.json()


# ─────────────────────────────────────────────────────────────────────────────
# 1. Auth / Connection
# ─────────────────────────────────────────────────────────────────────────────


def check_auth_status() -> dict:
    """
    Confirm the Gateway session is live and authenticated.
    Call this first – all other endpoints require an active session.
    """
    data = _get("/iserver/auth/status")
    authenticated = data.get("authenticated", False)
    connected = data.get("connected", False)
    print(f"[Auth] authenticated={authenticated}  connected={connected}")
    if not authenticated:
        print("       → Open https://localhost:5000 in your browser and log in.")
    return data


def tickle() -> dict:
    """
    Keep the session alive. The Gateway session times out after ~5 min of
    inactivity. Call this periodically in long-running scripts.
    """
    data = _post("/tickle")
    print(
        f"[Tickle] session kept alive – iserver connected: {data.get('iserver', {}).get('authStatus', {}).get('connected')}"
    )
    return data


def logout() -> dict:
    """Cleanly log out and close the Gateway session."""
    data = _post("/logout")
    print(f"[Logout] {data}")
    return data


# ─────────────────────────────────────────────────────────────────────────────
# 2. Account Info / Balances
# ─────────────────────────────────────────────────────────────────────────────


def get_accounts() -> list:
    """Return a list of all accounts linked to this login."""
    data = _get("/portfolio/accounts")
    for acct in data:
        print(
            f"[Account] id={acct.get('id')}  type={acct.get('type')}  currency={acct.get('currency')}"
        )
    return data


def get_account_summary(account_id: str) -> dict:
    """
    High-level summary: net liquidation value, buying power, cash, P&L.
    account_id: e.g. "U1234567"
    """
    data = _get(f"/portfolio/{account_id}/summary")
    fields = [
        "netliquidation",
        "totalcashvalue",
        "buyingpower",
        "unrealizedpnl",
        "realizedpnl",
    ]
    print(f"\n[Summary] {account_id}")
    for key in fields:
        entry = data.get(key, {})
        print(
            f"  {key:25s} {entry.get('amount', 'n/a'):>15}  {entry.get('currency', '')}"
        )
    return data


def get_positions(account_id: str) -> list:
    """Return all open positions for the account (page 0)."""
    data = _get(f"/portfolio/{account_id}/positions/0")
    print(f"\n[Positions] {account_id}")
    for pos in data:
        print(
            f"  {pos.get('ticker', ''):8s}  conid={pos.get('conid')}  "
            f"qty={pos.get('position')}  mktVal={pos.get('mktValue')}"
        )
    return data


# ─────────────────────────────────────────────────────────────────────────────
# 3. Market Data / Quotes
# ─────────────────────────────────────────────────────────────────────────────

# Common market-data field codes:
#   31   = Last Price
#   84   = Bid
#   86   = Ask
#   7295 = Open
#   7296 = Close (previous day)
#   7762 = Volume
DEFAULT_FIELDS = "31,84,86,7295,7296,7762"


def search_contract(symbol: str, sec_type: str = "STK") -> list:
    """
    Find the contract ID (conid) for a symbol.
    sec_type options: STK, OPT, FUT, CASH, CFD, etc.
    """
    data = _get(
        "/iserver/secdef/search", params={"symbol": symbol, "secType": sec_type}
    )
    print(f"\n[Contract search] '{symbol}'")
    for c in data:
        print(
            f"  conid={c.get('conid')}  company='{c.get('companyName', '')}'  "
            f"exchange={c.get('primaryExch', '')}"
        )
    return data


def get_market_snapshot(conids: list[int], fields: str = DEFAULT_FIELDS) -> list:
    """
    Request a snapshot of live market data for one or more contracts.
    conids: list of integer contract IDs, e.g. [265598]  (265598 = AAPL)
    Note: the first call often returns empty – retry once after a short delay.
    """
    conid_str = ",".join(str(c) for c in conids)
    data = _get(
        "/iserver/marketdata/snapshot", params={"conids": conid_str, "fields": fields}
    )

    # First call may return an empty/pending response – retry once
    if not data or data == [{}]:
        time.sleep(2)
        data = _get(
            "/iserver/marketdata/snapshot",
            params={"conids": conid_str, "fields": fields},
        )

    field_labels = {
        "31": "Last",
        "84": "Bid",
        "86": "Ask",
        "7295": "Open",
        "7296": "Prev Close",
        "7762": "Volume",
    }
    print(f"\n[Market Snapshot]")
    for item in data:
        ticker = item.get("55", item.get("conid", "?"))
        print(f"  {ticker}")
        for code, label in field_labels.items():
            if code in item:
                print(f"    {label:12s} {item[code]}")
    return data


def get_historical_bars(conid: int, period: str = "1w", bar: str = "1d") -> dict:
    """
    Fetch OHLCV bars for a contract.
    period: 1d, 1w, 1m, 3m, 6m, 1y
    bar:    1min, 5min, 15min, 1h, 1d, 1w, 1m
    """
    data = _get(
        f"/iserver/marketdata/history",
        params={"conid": conid, "period": period, "bar": bar, "outsideRth": False},
    )
    bars = data.get("data", [])
    print(
        f"\n[Historical bars] conid={conid}  period={period}  bar={bar}  → {len(bars)} bars"
    )
    for b in bars[-5:]:  # print last 5 bars
        print(
            f"  t={b.get('t')}  o={b.get('o')}  h={b.get('h')}  "
            f"l={b.get('l')}  c={b.get('c')}  v={b.get('v')}"
        )
    return data


# ─────────────────────────────────────────────────────────────────────────────
# 4. Orders
# ─────────────────────────────────────────────────────────────────────────────


def get_live_orders() -> list:
    """Return all open / recent orders."""
    data = _get("/iserver/account/orders")
    orders = data.get("orders", [])
    print(f"\n[Live orders] {len(orders)} order(s)")
    for o in orders:
        print(
            f"  orderId={o.get('orderId')}  ticker={o.get('ticker')}  "
            f"side={o.get('side')}  qty={o.get('remainingQuantity')}  "
            f"status={o.get('status')}"
        )
    return orders


def place_order(
    account_id: str,
    conid: int,
    side: str,
    quantity: int,
    order_type: str = "MKT",
    limit_price: float = None,
    tif: str = "DAY",
) -> list:
    """
    Submit a single order.

    Parameters
    ----------
    account_id : str    e.g. "U1234567"
    conid      : int    Contract ID (from search_contract)
    side       : str    "BUY" or "SELL"
    quantity   : int    Number of shares/contracts
    order_type : str    "MKT" | "LMT" | "STP" | "STP_LMT"
    limit_price: float  Required for LMT and STP_LMT orders
    tif        : str    "DAY" | "GTC" | "IOC" | "FOK"

    Returns a list of order confirmation objects.
    On success you usually get a reply-confirmation dict that needs a second
    POST to confirm (see confirm_order below).
    """
    order = {
        "conid": conid,
        "orderType": order_type,
        "side": side.upper(),
        "quantity": quantity,
        "tif": tif,
    }
    if limit_price is not None:
        order["price"] = limit_price

    payload = {"orders": [order]}
    data = _post(f"/iserver/account/{account_id}/orders", payload)
    print(f"\n[Place order] {side} {quantity}×conid{conid} @ {order_type}")
    print(f"  Response: {json.dumps(data, indent=2)}")
    return data


def confirm_order(reply_id: str, confirmed: bool = True) -> dict:
    """
    Some orders require a second confirmation step (e.g. "are you sure?").
    Pass the id returned in the place_order response.
    confirmed=True to proceed, False to cancel.
    """
    data = _post(f"/iserver/reply/{reply_id}", {"confirmed": confirmed})
    print(f"\n[Confirm order] reply_id={reply_id}  confirmed={confirmed}")
    print(f"  Response: {json.dumps(data, indent=2)}")
    return data


def cancel_order(account_id: str, order_id: str) -> dict:
    """Cancel an open order by its orderId."""
    data = _delete(f"/iserver/account/{account_id}/order/{order_id}")
    print(f"\n[Cancel order] orderId={order_id}  response={data}")
    return data


def modify_order(
    account_id: str,
    order_id: str,
    conid: int,
    quantity: int,
    order_type: str,
    limit_price: float = None,
    tif: str = "DAY",
) -> dict:
    """Modify price / quantity of an existing open order."""
    payload = {
        "conid": conid,
        "orderType": order_type,
        "quantity": quantity,
        "tif": tif,
    }
    if limit_price is not None:
        payload["price"] = limit_price
    data = _post(f"/iserver/account/{account_id}/order/{order_id}", payload)
    print(f"\n[Modify order] orderId={order_id}  response={data}")
    return data


# ─────────────────────────────────────────────────────────────────────────────
# Demo  –  runs through all four sections in sequence
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("IBKR Client Portal API – Demo")
    print("=" * 60)

    # ── 1. Auth ───────────────────────────────────────────────────────────────
    print("\n── 1. AUTH ──────────────────────────────────────────────")
    status = check_auth_status()
    if not status.get("authenticated"):
        print("Session not authenticated. Start the Gateway and log in first.")
        raise SystemExit(1)

    # ── 2. Account info ───────────────────────────────────────────────────────
    print("\n── 2. ACCOUNT ───────────────────────────────────────────")
    accounts = get_accounts()
    account_id = accounts[0]["id"]  # use your first account

    get_account_summary(account_id)
    get_positions(account_id)

    # ── 3. Market data ────────────────────────────────────────────────────────
    print("\n── 3. MARKET DATA ───────────────────────────────────────")

    # Find AAPL's contract ID
    results = search_contract("AAPL", "STK")
    aapl_conid = results[0]["conid"]  # typically 265598

    # Live snapshot (bid/ask/last)
    get_market_snapshot([aapl_conid])

    # Historical OHLCV bars
    get_historical_bars(aapl_conid, period="1w", bar="1d")

    # ── 4. Orders (paper account recommended for testing!) ────────────────────
    print("\n── 4. ORDERS ─────────────────────────────────────────────")
    get_live_orders()

    # --- Uncomment below to place a real paper-trading order ---
    #
    # resp = place_order(
    #     account_id = account_id,
    #     conid      = aapl_conid,
    #     side       = "BUY",
    #     quantity   = 1,
    #     order_type = "LMT",
    #     limit_price= 180.00,
    #     tif        = "DAY",
    # )
    #
    # # Some orders require a confirmation reply
    # if resp and isinstance(resp, list) and "id" in resp[0]:
    #     confirm_order(resp[0]["id"], confirmed=True)
    #

    # ── Keep alive example ────────────────────────────────────────────────────
    print("\n── TICKLE (keep-alive) ───────────────────────────────────")
    tickle()

    print("\nDone.")
