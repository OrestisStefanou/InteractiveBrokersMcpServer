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
    AccountSummary,
    CurrencyBalance,
    LiveOrder,
    OrderPlacementResult,
    OrderPlacementStatus,
    OrderSide,
    OrderStatus,
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


def _amount(value: ib_models.AccountSummaryValue | None) -> float | None:
    # IB reports a field it has no value for as isNull with an amount of 0.
    # Passing that through would read as a genuine zero balance.
    if value is None or value.is_null:
        return None
    return value.amount


@tool(
    name="getAccountSummary",
    description=(
        "Get the balance and margin summary of an Interactive Brokers account: net "
        "liquidation value, cash, buying power, available funds, excess liquidity, "
        "margin requirements and profit and loss. Every amount is in the account's "
        "base currency. Use getAccountBalances instead for a per-currency cash "
        "breakdown."
    ),
)
async def get_ib_account_summary(
    account_id: Annotated[str, "the account ID to get the balance summary for"],
    ib_client: InteractiveBrokersClient = Depends(get_interactive_brokers_client),
) -> AccountSummary:
    result = await ib_client.get_account_summary(account_id)

    # Every amount in the summary is denominated in the account's base currency,
    # so read it off whichever monetary field IB populated.
    currency = next(
        (
            value.currency
            for value in (
                result.net_liquidation,
                result.total_cash_value,
                result.excess_liquidity,
            )
            if value is not None and value.currency
        ),
        None,
    )

    return AccountSummary(
        currency=currency,
        net_liquidation=_amount(result.net_liquidation),
        total_cash_value=_amount(result.total_cash_value),
        settled_cash=_amount(result.settled_cash),
        accrued_cash=_amount(result.accrued_cash),
        buying_power=_amount(result.buying_power),
        available_funds=_amount(result.available_funds),
        excess_liquidity=_amount(result.excess_liquidity),
        equity_with_loan_value=_amount(result.equity_with_loan_value),
        gross_position_value=_amount(result.gross_position_value),
        initial_margin_requirement=_amount(result.init_margin_req),
        maintenance_margin_requirement=_amount(result.maint_margin_req),
        cushion=_amount(result.cushion),
        unrealized_pnl=_amount(result.unrealized_pnl),
        realized_pnl=_amount(result.realized_pnl),
        day_trades_remaining=_amount(result.day_trades_remaining),
        # accounttype carries its payload as a string rather than an amount.
        account_type=(
            result.account_type.value if result.account_type is not None else None
        ),
    )


@tool(
    name="getAccountBalances",
    description=(
        "Get the cash balances of an Interactive Brokers account broken down by "
        "currency. The 'BASE' entry is the account-wide total converted into the "
        "account's base currency and the remaining entries are the individual "
        "currencies held, so summing across entries double counts. Use "
        "getAccountSummary instead for buying power and margin figures."
    ),
)
async def get_ib_account_balances(
    account_id: Annotated[str, "the account ID to get the cash balances for"],
    ib_client: InteractiveBrokersClient = Depends(get_interactive_brokers_client),
) -> list[CurrencyBalance]:
    results = await ib_client.get_account_ledger(account_id)
    return [
        CurrencyBalance(
            currency=result.currency,
            cash_balance=result.cash_balance,
            settled_cash=result.settled_cash,
            net_liquidation_value=result.net_liquidation_value,
            stock_market_value=result.stock_market_value,
            exchange_rate=result.exchange_rate,
            unrealized_pnl=result.unrealized_pnl,
            realized_pnl=result.realized_pnl,
            interest=result.interest,
            dividends=result.dividends,
        )
        for result in results
    ]


def _to_order_side(value: str | None) -> OrderSide | None:
    # The order status endpoint reports "B" and "S" while live orders report
    # "BUY" and "SELL".
    match (value or "").strip().upper():
        case "B" | "BUY":
            return OrderSide.BUY
        case "S" | "SELL":
            return OrderSide.SELL
        case _:
            return None


@tool(
    name="getOrderStatus",
    description=(
        "Get the current status of a single Interactive Brokers order by its order ID, "
        "including how much of it has filled and at what average price. Use the "
        "order_id returned by placeOrder. An order has only reached the market once "
        "its status is Submitted or beyond; PendingSubmit and PreSubmitted mean it is "
        "still on its way. Use getLiveOrders instead to find an order whose order ID "
        "is unknown."
    ),
)
async def get_ib_order_status(
    order_id: Annotated[str, "the Interactive Brokers order ID to look up"],
    ib_client: InteractiveBrokersClient = Depends(get_interactive_brokers_client),
) -> OrderStatus:
    result = await ib_client.get_order_status(order_id)

    # IB reports the total and the cumulative fill but no outstanding figure on
    # this endpoint, unlike the live orders endpoint.
    remaining_quantity = None
    if result.total_size is not None and result.cum_fill is not None:
        remaining_quantity = result.total_size - result.cum_fill

    return OrderStatus(
        order_id=result.order_id,
        status=result.order_status,
        status_description=result.order_status_description,
        side=_to_order_side(result.side),
        symbol=result.symbol,
        company_name=result.company_name,
        contract_id=result.conid,
        sec_type=result.sec_type,
        listing_exchange=result.listing_exchange,
        currency=result.currency,
        order_type=result.order_type,
        total_quantity=result.total_size,
        filled_quantity=result.cum_fill,
        remaining_quantity=remaining_quantity,
        average_price=result.average_price,
        limit_price=result.price,
        stop_price=result.stop_price,
        time_in_force=result.tif,
        outside_regular_trading_hours=result.outside_rth,
        order_time=result.order_time,
        description=(
            result.order_description_with_contract or result.order_description
        ),
        cannot_cancel=result.cannot_cancel_order,
    )


@tool(
    name="getLiveOrders",
    description=(
        "List the open and recently completed orders of an Interactive Brokers "
        "account, with the fill progress of each. Use this to find an order whose "
        "order ID is unknown, in particular to reconcile a placeOrder call whose "
        "outcome was unclear: match the client_order_id on each entry against the one "
        "that call returned. Interactive Brokers serves this endpoint in polling mode, "
        "so the first call of a session can come back empty or incomplete while it "
        "builds the snapshot; call again before concluding an order does not exist."
    ),
)
async def get_ib_live_orders(
    account_id: Annotated[
        str | None, "restrict the results to a single account ID"
    ] = None,
    ib_client: InteractiveBrokersClient = Depends(get_interactive_brokers_client),
) -> list[LiveOrder]:
    results = await ib_client.get_live_orders(account_id=account_id)
    return [
        LiveOrder(
            order_id=result.order_id,
            client_order_id=result.order_ref,
            account_id=result.account,
            status=result.status,
            side=_to_order_side(result.side),
            ticker=result.ticker,
            company_name=result.company_name,
            contract_id=result.conid,
            sec_type=result.sec_type,
            listing_exchange=result.listing_exchange,
            currency=result.currency,
            order_type=result.order_type or result.orig_order_type,
            total_quantity=result.total_size,
            filled_quantity=result.filled_quantity,
            remaining_quantity=result.remaining_quantity,
            average_price=result.avg_price,
            limit_price=result.price,
            stop_price=result.stop_price,
            time_in_force=result.time_in_force,
            last_execution_time=result.last_execution_time,
            description=result.order_desc,
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
            f"{client_order_id}). Call getLiveOrders and look for that client order id "
            f"before retrying. Raw response: {exc.payload!r}"
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
            "response, so the order may already be placed. Call getLiveOrders to check "
            f"the account's orders before retrying. Raw response: {exc.payload!r}"
        ) from exc

    return [_to_order_placement_result(result) for result in results]
