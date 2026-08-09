import uuid
from typing import Annotated

from fastmcp.dependencies import Depends
from fastmcp.exceptions import ToolError
from fastmcp.tools import tool
from pydantic import ValidationError

from interactive_brokers import models as ib_models
from interactive_brokers.errors import OrderResponseParseError
from interactive_brokers.ib_client import InteractiveBrokersClient
from mcp_app.dependencies import get_interactive_brokers_client
from mcp_app.schema import (
    Account,
    OrderPlacementResult,
    OrderPlacementStatus,
    OrderSide,
    Position,
    SecurityInformation,
    SecuritySearchResult,
    SecurityType,
    TimeInForce,
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
    description="Get detailed information about an Interactive Brokers security by its contract ID.",
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


def _to_order_placement_result(
    response: ib_models.PlaceOrderResponse,
    client_order_id: str | None = None,
) -> OrderPlacementResult:
    if response.error is not None:
        status = OrderPlacementStatus.REJECTED
    elif response.id is not None and response.message is not None:
        status = OrderPlacementStatus.NEEDS_CONFIRMATION
    elif response.order_id is not None:
        status = OrderPlacementStatus.SUBMITTED
    else:
        status = OrderPlacementStatus.UNKNOWN

    return OrderPlacementResult(
        status=status,
        client_order_id=client_order_id,
        order_id=response.order_id,
        order_status=response.order_status,
        reply_id=(
            response.id
            if status == OrderPlacementStatus.NEEDS_CONFIRMATION
            else None
        ),
        messages=response.message,
        error=response.error,
    )


@tool(
    name="placeOrder",
    description=(
        "Place a market order on Interactive Brokers. A market order executes "
        "immediately at the prevailing market price, which may differ from the last "
        "quoted price. Limit orders are not supported. Interactive Brokers often "
        "responds with warnings that must be reviewed: a NEEDS_CONFIRMATION result "
        "means the order has NOT been sent to the market and only goes live after "
        "calling confirmOrder with the returned reply_id. A SUBMITTED result is "
        "final and needs no follow-up call."
    ),
    annotations={"destructiveHint": True, "readOnlyHint": False},
)
async def place_ib_order(
    account_id: Annotated[str, "the account ID to place the order in"],
    contract_id: Annotated[int, "contract id of the security to trade"],
    side: Annotated[OrderSide, "whether to buy or sell"],
    quantity: Annotated[float, "number of shares or contracts to trade"],
    time_in_force: Annotated[
        TimeInForce, "how long the order stays active"
    ] = TimeInForce.DAY,
    ib_client: InteractiveBrokersClient = Depends(get_interactive_brokers_client),
) -> list[OrderPlacementResult]:
    match side:
        case OrderSide.BUY:
            ib_side = ib_models.OrderSide.BUY
        case OrderSide.SELL:
            ib_side = ib_models.OrderSide.SELL

    match time_in_force:
        case TimeInForce.DAY:
            ib_tif = ib_models.TimeInForce.DAY
        case TimeInForce.GTC:
            ib_tif = ib_models.TimeInForce.GTC
        case TimeInForce.IOC:
            ib_tif = ib_models.TimeInForce.IOC
        case TimeInForce.OPG:
            ib_tif = ib_models.TimeInForce.OPG

    client_order_id = uuid.uuid4().hex

    try:
        order_request = ib_models.PlaceOrderRequest(
            conid=contract_id,
            order_type=ib_models.OrderType.MARKET,
            side=ib_side,
            quantity=quantity,
            c_oid=client_order_id,
            tif=ib_tif,
            acct_id=account_id,
        )
    except ValidationError as exc:
        raise ToolError(f"Invalid order: {exc}") from exc

    try:
        results = await ib_client.place_order(
            account_id=account_id,
            order=order_request,
        )
    except OrderResponseParseError as exc:
        raise ToolError(
            "Interactive Brokers accepted the request but returned an unreadable "
            f"response, so the order may already be placed (client order id "
            f"{client_order_id}). Reconcile against the account's live orders before "
            f"retrying. Raw response: {exc.payload!r}"
        ) from exc

    return [_to_order_placement_result(result, client_order_id) for result in results]


@tool(
    name="confirmOrder",
    description=(
        "Confirm or cancel an order that Interactive Brokers flagged with a warning. "
        "Only call this with a reply_id returned by a NEEDS_CONFIRMATION result from "
        "placeOrder; there is nothing to confirm otherwise. Pass confirmed=true to "
        "send the order to the market, or confirmed=false to abandon it. Interactive "
        "Brokers may respond with a further warning, in which case another "
        "NEEDS_CONFIRMATION result is returned and must be confirmed with the new "
        "reply_id."
    ),
    annotations={"destructiveHint": True, "readOnlyHint": False},
)
async def confirm_ib_order(
    reply_id: Annotated[str, "the reply id of the warning to answer"],
    confirmed: Annotated[bool, "true to place the order, false to abandon it"] = True,
    ib_client: InteractiveBrokersClient = Depends(get_interactive_brokers_client),
) -> list[OrderPlacementResult]:
    try:
        results = await ib_client.confirm_order(
            reply_id=reply_id,
            confirmed=confirmed,
        )
    except OrderResponseParseError as exc:
        raise ToolError(
            "Interactive Brokers accepted the confirmation but returned an unreadable "
            "response, so the order may already be placed. Reconcile against the "
            f"account's live orders before retrying. Raw response: {exc.payload!r}"
        ) from exc

    return [_to_order_placement_result(result) for result in results]
