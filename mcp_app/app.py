import logging

from fastmcp import FastMCP
from fastmcp.server.middleware import (
    Middleware,
    MiddlewareContext,
)

from mcp_app.tools import (
    get_ib_accounts,
    get_ib_security_by_contract_id,
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
