# InteractiveBrokersMcpServer

An MCP server that exposes tools to interact with your Interactive Brokers account via the IB Client Portal Gateway.

## Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) package manager
- Java 1.8 update 192+ (required for the IB Client Portal Gateway)
- An Interactive Brokers account

## Setup

### 1. Start the IB Client Portal Gateway

The IB Client Portal Gateway acts as a local proxy to the IB API. It is bundled in the `ib_clientportal/` directory.

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

# Set to true to disable all tools that modify account state (default: false)
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
http://localhost:9092
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
