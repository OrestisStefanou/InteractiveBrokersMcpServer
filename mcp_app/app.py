import logging

from fastmcp import FastMCP
from fastmcp.server.middleware import (
    Middleware,
    MiddlewareContext,
)

from config import settings
from mcp_app.tools import (
    confirm_ib_order,
    get_ib_account_balances,
    get_ib_account_positions,
    get_ib_account_summary,
    get_ib_accounts,
    get_ib_security_by_contract_id,
    place_ib_order,
    search_ib_securities,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class LoggingMiddleware(Middleware):
    async def on_call_tool(self, context: MiddlewareContext, call_next):
        tool_name = context.message.name
        args = context.message.arguments
        logger.info("Calling tool %s with arguments %s", tool_name, args)
        result = await call_next(context)
        logger.info(
            "Tool call %s with arguments %s returned result %s", tool_name, args, result
        )
        return result


mcp_app = FastMCP("Interactive Brokers MCP Server")
mcp_app.add_middleware(LoggingMiddleware())
mcp_app.add_tool(get_ib_accounts)
mcp_app.add_tool(search_ib_securities)
mcp_app.add_tool(get_ib_security_by_contract_id)
mcp_app.add_tool(get_ib_account_positions)
mcp_app.add_tool(get_ib_account_summary)
mcp_app.add_tool(get_ib_account_balances)

if settings.read_only:
    logger.info("read_only is enabled, order placement tools are not registered")
else:
    mcp_app.add_tool(place_ib_order)
    mcp_app.add_tool(confirm_ib_order)
