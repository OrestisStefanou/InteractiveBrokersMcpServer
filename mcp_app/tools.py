from typing import Annotated

from fastmcp.dependencies import Depends
from fastmcp.exceptions import ToolError
from fastmcp.tools import tool

from interactive_brokers import models as ib_models
from interactive_brokers.ib_client import InteractiveBrokersClient
from mcp_app.dependencies import get_interactive_brokers_client
from mcp_app.schema import (
    SecuritySearchResult,
    SecurityType,
)


@tool(
    name="searchInteractiveBrokersSecurities",
    description="Search for Interactive Brokers securities using symbol OR name.",
)
async def search_ib_securities(
    symbol: Annotated[str | None, "symbol of the security"] = None,
    name: Annotated[str | None, "name of the security"] = None,
    security_type: Annotated[SecurityType | None, "type of the security"] = None,
    ib_client: InteractiveBrokersClient = Depends(get_interactive_brokers_client),
) -> list[SecuritySearchResult]:
    if symbol is None and name is None:
        raise ToolError("Either symbol or name must be provided")

    ib_request_symbol = symbol if symbol is not None else name
    ib_request_uses_name = True if name is not None else False
    ib_sec_type = None
    if security_type is not None:
        ib_sec_type = ib_models.SecurityType(security_type.value)

    search_request = ib_models.SearchContractRequest(
        symbol=ib_request_symbol,
        name=ib_request_uses_name,
        security_type=ib_sec_type,
    )
    search_results = await ib_client.search_contract(search_request)

    return [
        SecuritySearchResult(
            conid=result.conid,
            company_header=result.company_header,
            company_name=result.company_name,
            symbol=result.symbol,
            description=result.description,
            restricted=result.restricted,
            bondid=result.bondid,
        )
        for result in search_results
    ]
