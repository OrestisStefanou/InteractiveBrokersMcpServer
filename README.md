# InteractiveBrokersMcpServer

An MCP server that exposes tools to interact with your Interactive Brokers account via the IB Client Portal Gateway.

## Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) package manager
- Java 1.8 update 192+ (required for the IB Client Portal Gateway)
- An Interactive Brokers account

## Setup

### 1. Start the IB Client Portal Gateway

The IB Client Portal Gateway acts as a local proxy to the IB API. It is not bundled with this repository. Download it from [Interactive Brokers](https://www.interactivebrokers.com/en/trading/ib-api.php#client-portal-api) and unpack it into an `ib_clientportal/` directory in the project root (that path is gitignored).

**macOS / Linux:**
```bash
cd ib_clientportal
bin/run.sh root/conf.yaml
```

**Windows:**
```bat
cd ib_clientportal
bin\run.bat root\conf.yaml
```

Once running, the gateway listens on `https://localhost:5000` by default.

### 2. Authenticate with Interactive Brokers

Open your browser and navigate to `https://localhost:5000`. Log in with your IB credentials. After a successful login you can close the browser — the gateway remains authenticated.

### 3. Install dependencies

```bash
uv sync
```

### 4. Configure the server

Create a `.env` file in the project root to override any defaults:

```env
# URL of the IB Client Portal Gateway (default: https://localhost:5000/v1/api)
INTERACTIVE_BROKERS_PORTAL_BASE_URL=https://localhost:5000/v1/api

# Port the MCP server listens on (default: 9092)
MCP_PORT=9092

# Set to true to hide the tools that modify account state (default: false)
READ_ONLY=false
```

All fields are optional — the defaults work out of the box if the gateway is running on its default port.

### 5. Run the MCP server

```bash
uv run python main.py
```

The server starts in HTTP transport mode on the configured port (default `9092`).

## Connecting an MCP client

Point your MCP client at:

```
http://localhost:9092/mcp
```

For Claude Desktop, add the following to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "interactive-brokers": {
      "url": "http://localhost:9092/mcp"
    }
  }
}
```

## Available tools

| Tool | Description |
|---|---|
| `getAccounts` | Get all IB accounts linked to the current login |
| `searchSecurities` | Search for securities by symbol or name |
| `getSecurityInfoByContractId` | Get detailed security information by contract ID |
| `getAccountPositions` | Get the list of positions held in a given account |
| `getAccountSummary` | Get balance and margin figures for an account, in its base currency |
| `getAccountBalances` | Get cash balances for an account, broken down by currency |
| `getOrderStatus` | Get the status and fill progress of a single order by order ID |
| `getLiveOrders` | List open and recently completed orders |
| `getTrades` | List executions across an account, last 7 days |
| `getTransactionHistory` | Get up to 90 days of transactions for one security |
| `placeOrder` | Place a market order (write tool) |
| `confirmOrder` | Answer an IB warning to release or abandon an order (write tool) |

### Reading balances

The two balance tools answer different questions and are backed by different IB endpoints.

`getAccountSummary` (`/portfolio/{accountId}/summary`) answers "what can I trade with": net liquidation value, total and settled cash, buying power, available funds, excess liquidity, margin requirements, cushion and P&L. Every amount is in the account's base currency. IB flags a field it has no value for as null with an amount of 0; the server maps those to `null` so they are not mistaken for a genuine zero balance.

`getAccountBalances` (`/portfolio/{accountId}/ledger`) answers "what cash do I hold": one entry per currency, with cash balance, settled cash, net liquidation value, stock market value, exchange rate and P&L. The `BASE` entry is the account-wide total converted into the base currency and the remaining entries are the individual currencies held, so summing across entries double counts.

### Reading history

IB splits transaction history across two endpoints, and neither one covers the whole job.

`getTrades` (`/iserver/account/trades`) lists executions across the account, optionally filtered to one account, with the side, quantity, price, commission and net amount of each. IB serves at most 7 days here and the tool rejects a larger `days` rather than silently truncating the window. It covers executions only, so dividends and cash transfers never appear.

`getTransactionHistory` (`/pa/transactions`) reaches back up to 90 days and does include dividends and transfers, but IB only honours one contract per call, so a `contract_id` is required. That makes it a per-security tool rather than an account-wide one. `getAccountPositions` is the usual way to find the contract IDs to ask about, though note it only returns securities currently held, so a position closed inside the window will not show up that way.

Neither endpoint reaches further than 90 days. Anything older needs IB's Flex Query service, which is a separate system and is not exposed here.

`quantity` on a transaction is signed, negative for sells and positive for buys, unlike the `getTrades` quantity which is the absolute size of the fill.

### Placing orders

`placeOrder` supports market orders only. Limit orders are not exposed yet.

IB frequently answers an order with a warning rather than a confirmation. The server never accepts those warnings on your behalf: `placeOrder` returns `status: NEEDS_CONFIRMATION` together with a `reply_id` and the warning text, and the order stays off the market until `confirmOrder` is called with that `reply_id`. IB may raise a further warning in response, which returns another `NEEDS_CONFIRMATION` to confirm in turn.

Every result carries a `client_order_id` generated by the server. If a call fails in a way that leaves the outcome unclear, call `getLiveOrders` and match that value against the `client_order_id` of each entry before retrying. IB files the client order id under `order_ref`, which the tool surfaces as `client_order_id`.

### Checking orders

`getOrderStatus` (`/iserver/account/order/status/{orderId}`) takes an order ID and returns the status, fill progress and average fill price of that one order. An order has only reached the market once its status is `Submitted` or beyond; `PendingSubmit` and `PreSubmitted` mean it is still on its way. IB reports the total size and the cumulative fill on this endpoint but no outstanding figure, so `remaining_quantity` is derived by the server and is null when either input is missing.

`getLiveOrders` (`/iserver/account/orders`) lists open and recently completed orders, optionally filtered to one account. Use it when the order ID is unknown. IB serves this endpoint in polling mode, so the first call of a session can come back empty or incomplete while it builds the snapshot; call again before concluding an order does not exist.

Both endpoints report quantities and prices as strings, and send an empty string rather than null for a figure they have no value for. Those are parsed to `null` rather than `0`. The two also disagree on how they spell the order side, `B`/`S` versus `BUY`/`SELL`, which the server normalises to `BUY`/`SELL` in both tools.

`placeOrder` and `confirmOrder` are the only tools that modify account state, so both are omitted from the tool list when `READ_ONLY=true`.

## Running tests

```bash
uv sync
uv run pytest
```

The suite mocks the gateway with `respx`, so it never talks to Interactive Brokers.
