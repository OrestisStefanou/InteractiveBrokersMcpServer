from typing import Annotated

from fastmcp.dependencies import Depends
from fastmcp.exceptions import ToolError
from fastmcp.tools import tool

from interactive_brokers import models as ib_models
from interactive_brokers.ib_client import InteractiveBrokersClient
from mcp_app.dependencies import get_interactive_brokers_client
from mcp_app.schema import (
    Account,
    Position,
    SecurityInformation,
    SecuritySearchResult,
    SecurityType,
    SortDirection,
)


@tool(
    name="getAccounts",
    description="Get all Interactive Brokers accounts linked to the current login.",
)
async def get_ib_accounts(
    ib_client: InteractiveBrokersClient = Depends(get_interactive_brokers_client),
) -> list[Account]:
    results = await ib_client.get_accounts()
    return [
        Account(
            id=account.id,
            account_van=account.account_van,
            account_title=account.account_title,
            display_name=account.display_name,
            account_alias=account.account_alias,
            account_status=account.account_status,
            currency=account.currency,
            type=account.type,
            trading_type=account.trading_type,
            business_type=account.business_type,
            ib_entity=account.ib_entity,
            fa_client=account.fa_client,
            clearing_status=account.clearing_status,
            covestor=account.covestor,
            no_client_trading=account.no_client_trading,
            track_virtual_fx_portfolio=account.track_virtual_fx_portfolio,
            desc=account.desc,
        )
        for account in results
    ]


@tool(
    name="searchSecurities",
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
        match security_type:
            case SecurityType.STOCK:
                ib_sec_type = ib_models.SecurityType.STOCK
            case SecurityType.INDEX:
                ib_sec_type = ib_models.SecurityType.INDEX
            case SecurityType.BOND:
                ib_sec_type = ib_models.SecurityType.BOND

    search_request = ib_models.SearchContractRequest(
        symbol=ib_request_symbol,
        name=ib_request_uses_name,
        security_type=ib_sec_type,
    )
    search_results = await ib_client.search_contract(search_request)

    return [
        SecuritySearchResult(
            contract_id=result.conid,
            company_header=result.company_header,
            company_name=result.company_name,
            symbol=result.symbol,
            description=result.description,
            restricted=result.restricted,
            bondid=result.bondid,
        )
        for result in search_results
    ]


@tool(
    name="getSecurityInfoByContractId",
    description="Search for Interactive Brokers securities using symbol OR name.",
)
async def get_ib_security_by_contract_id(
    contract_id: Annotated[str, "contract id of the security"],
    ib_client: InteractiveBrokersClient = Depends(get_interactive_brokers_client),
) -> SecurityInformation:
    result = await ib_client.get_security_info_by_contract_id(contract_id)
    return SecurityInformation(
        contract_id=result.con_id,
        symbol=result.symbol,
        currency=result.currency,
        company_name=result.company_name,
        instrument_type=result.instrument_type,
        exchange=result.exchange,
        valid_exchanges=result.valid_exchanges,
        trading_class=result.trading_class,
        industry=result.industry,
        category=result.category,
        local_symbol=result.local_symbol,
        cfi_code=result.cfi_code,
        cusip=result.cusip,
        expiry_full=result.expiry_full,
        maturity_date=result.maturity_date,
    )


@tool(
    name="getAccountPositions",
    description="Get the list of positions held in a given Interactive Brokers account.",
)
async def get_ib_account_positions(
    account_id: Annotated[str, "the account ID to get positions for"],
    ib_client: InteractiveBrokersClient = Depends(get_interactive_brokers_client),
) -> list[Position]:
    results = await ib_client.get_account_positions(
        account_id=account_id,
    )
    return [
        Position(
            position=result.position,
            contract_id=result.conid,
            avg_cost=result.avg_cost,
            avg_price=result.avg_price,
            currency=result.currency,
            symbol=result.description,
            market_price=result.market_price,
            market_value=result.market_value,
            realized_pnl=result.realized_pnl,
            unrealized_pnl=result.unrealized_pnl,
            sec_type=result.sec_type,
            asset_class=result.asset_class,
            timestamp=result.timestamp,
        )
        for result in results
    ]
