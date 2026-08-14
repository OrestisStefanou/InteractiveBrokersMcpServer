import enum
from typing import Annotated, Any, TypeAlias

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    model_validator,
)


def _blank_to_none(value: Any) -> Any:
    # The order endpoints report a number they have no value for as an empty
    # string rather than omitting the field or sending null, and "" is not
    # parseable as a float.
    if isinstance(value, str) and not value.strip():
        return None
    return value


IbFloat: TypeAlias = Annotated[float | None, BeforeValidator(_blank_to_none)]
IbInt: TypeAlias = Annotated[int | None, BeforeValidator(_blank_to_none)]


class SecurityType(enum.StrEnum):
    STOCK = "STK"
    INDEX = "IND"
    BOND = "BOND"


class SearchContractRequest(BaseModel):
    model_config = ConfigDict(
        use_enum_values=True,
        validate_by_name=True,
    )

    symbol: str
    name: bool | None = None
    security_type: SecurityType | None = Field(default=None, alias="secType")


class Section(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    sec_type: str = Field(alias="secType")
    months: str | None = None
    exchange: str | None = None
    show_prips: bool | None = Field(default=None, alias="showPrips")
    conid: str | None = None
    leg_sec_type: str | None = Field(default=None, alias="legSecType")


class Issuer(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str


class SearchContractResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    conid: str
    company_header: str = Field(alias="companyHeader")
    company_name: str | None = Field(default=None, alias="companyName")
    symbol: str | None = None
    description: str | None = None
    restricted: str | None = None
    sections: list[Section] = []
    issuers: list[Issuer] | None = None
    bondid: int | None = None


SearchContractsResponse: TypeAlias = list[SearchContractResult]


class Account(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    account_id: str | None = Field(default=None, alias="accountId")
    account_van: str | None = Field(default=None, alias="accountVan")
    account_title: str | None = Field(default=None, alias="accountTitle")
    display_name: str | None = Field(default=None, alias="displayName")
    account_alias: str | None = Field(default=None, alias="accountAlias")
    account_status: int | None = Field(default=None, alias="accountStatus")
    currency: str | None = None
    type: str | None = None
    trading_type: str | None = Field(default=None, alias="tradingType")
    business_type: str | None = Field(default=None, alias="businessType")
    ib_entity: str | None = Field(default=None, alias="ibEntity")
    fa_client: bool | None = Field(default=None, alias="faclient")
    clearing_status: str | None = Field(default=None, alias="clearingStatus")
    covestor: bool | None = None
    no_client_trading: bool | None = Field(default=None, alias="noClientTrading")
    track_virtual_fx_portfolio: bool | None = Field(
        default=None, alias="trackVirtualFXPortfolio"
    )
    desc: str | None = None


class Position(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    position: float | None = None
    conid: str | None = None
    avg_cost: float | None = Field(default=None, alias="avgCost")
    avg_price: float | None = Field(default=None, alias="avgPrice")
    currency: str | None = None
    description: str | None = None
    is_last_to_loq: bool | None = Field(default=None, alias="isLastToLoq")
    market_price: float | None = Field(default=None, alias="marketPrice")
    market_value: float | None = Field(default=None, alias="marketValue")
    realized_pnl: float | None = Field(default=None, alias="realizedPnl")
    sec_type: str | None = Field(default=None, alias="secType")
    timestamp: int | None = None
    unrealized_pnl: float | None = Field(default=None, alias="unrealizedPnl")
    asset_class: str | None = Field(default=None, alias="assetClass")
    sector: str | None = None
    group: str | None = None
    model: str | None = None


class AccountSummaryValue(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    amount: float | None = None
    currency: str | None = None
    # IB reports a field it has no value for as isNull with an amount of 0.
    is_null: bool | None = Field(default=None, alias="isNull")
    value: str | None = None
    severity: int | None = None
    timestamp: int | None = None


class AccountSummary(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    net_liquidation: AccountSummaryValue | None = Field(
        default=None, alias="netliquidation"
    )
    total_cash_value: AccountSummaryValue | None = Field(
        default=None, alias="totalcashvalue"
    )
    settled_cash: AccountSummaryValue | None = Field(default=None, alias="settledcash")
    accrued_cash: AccountSummaryValue | None = Field(default=None, alias="accruedcash")
    buying_power: AccountSummaryValue | None = Field(default=None, alias="buyingpower")
    available_funds: AccountSummaryValue | None = Field(
        default=None, alias="availablefunds"
    )
    excess_liquidity: AccountSummaryValue | None = Field(
        default=None, alias="excessliquidity"
    )
    equity_with_loan_value: AccountSummaryValue | None = Field(
        default=None, alias="equitywithloanvalue"
    )
    gross_position_value: AccountSummaryValue | None = Field(
        default=None, alias="grosspositionvalue"
    )
    init_margin_req: AccountSummaryValue | None = Field(
        default=None, alias="initmarginreq"
    )
    maint_margin_req: AccountSummaryValue | None = Field(
        default=None, alias="maintmarginreq"
    )
    cushion: AccountSummaryValue | None = None
    leverage: AccountSummaryValue | None = None
    sma: AccountSummaryValue | None = None
    unrealized_pnl: AccountSummaryValue | None = Field(
        default=None, alias="unrealizedpnl"
    )
    realized_pnl: AccountSummaryValue | None = Field(default=None, alias="realizedpnl")
    day_trades_remaining: AccountSummaryValue | None = Field(
        default=None, alias="daytradesremaining"
    )
    account_type: AccountSummaryValue | None = Field(default=None, alias="accounttype")


class LedgerEntry(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    # Always populated by the client from the key IB filed the entry under.
    currency: str
    cash_balance: float | None = Field(default=None, alias="cashbalance")
    settled_cash: float | None = Field(default=None, alias="settledcash")
    net_liquidation_value: float | None = Field(
        default=None, alias="netliquidationvalue"
    )
    stock_market_value: float | None = Field(default=None, alias="stockmarketvalue")
    exchange_rate: float | None = Field(default=None, alias="exchangerate")
    unrealized_pnl: float | None = Field(default=None, alias="unrealizedpnl")
    realized_pnl: float | None = Field(default=None, alias="realizedpnl")
    interest: float | None = None
    dividends: float | None = None
    funds: float | None = None
    money_funds: float | None = Field(default=None, alias="moneyfunds")
    cash_balance_fx_segment: float | None = Field(
        default=None, alias="cashbalancefxsegment"
    )
    stock_option_market_value: float | None = Field(
        default=None, alias="stockoptionmarketvalue"
    )
    future_market_value: float | None = Field(default=None, alias="futuremarketvalue")
    futures_only_pnl: float | None = Field(default=None, alias="futuresonlypnl")
    commodity_market_value: float | None = Field(
        default=None, alias="commoditymarketvalue"
    )
    corporate_bonds_market_value: float | None = Field(
        default=None, alias="corporatebondsmarketvalue"
    )
    acct_code: str | None = Field(default=None, alias="acctcode")
    second_key: str | None = Field(default=None, alias="secondkey")
    timestamp: int | None = None
    severity: int | None = None


class OrderType(enum.StrEnum):
    MARKET = "MKT"
    LIMIT = "LMT"


class OrderSide(enum.StrEnum):
    BUY = "BUY"
    SELL = "SELL"


class TimeInForce(enum.StrEnum):
    GTC = "GTC"
    OPG = "OPG"
    DAY = "DAY"
    IOC = "IOC"


class PlaceOrderRequest(BaseModel):
    model_config = ConfigDict(
        use_enum_values=True,
        validate_by_name=True,
        populate_by_name=True,
        validate_default=True,
    )

    conid: int
    order_type: OrderType = Field(alias="orderType")
    side: OrderSide
    quantity: float
    c_oid: str
    tif: TimeInForce = TimeInForce.DAY
    # Required for LIMIT orders.
    price: float | None = None
    acct_id: str | None = Field(default=None, alias="acctId")
    outside_rth: bool | None = Field(default=None, alias="outsideRTH")

    @model_validator(mode="after")
    def _require_price_for_limit_orders(self) -> "PlaceOrderRequest":
        if self.order_type == OrderType.LIMIT and self.price is None:
            raise ValueError("price is required for LIMIT orders")
        return self


class PlaceOrderResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    # Standard confirmation response.
    order_id: str | None = Field(default=None, alias="order_id")
    order_status: str | None = None
    encrypt_message: str | None = None
    # Alternate response: warning that must be confirmed via the reply endpoint.
    id: str | None = None
    message: list[str] | None = None
    is_suppressed: bool | None = Field(default=None, alias="isSuppressed")
    message_ids: list[str] | None = Field(default=None, alias="messageIds")
    # Reject response.
    error: str | None = None


class OrderStatus(BaseModel):
    # This endpoint already answers in snake_case, so no aliases are needed.
    model_config = ConfigDict(populate_by_name=True)

    order_id: IbInt = None
    account: str | None = None
    conid: IbInt = None
    symbol: str | None = None
    company_name: str | None = None
    sec_type: str | None = None
    listing_exchange: str | None = None
    currency: str | None = None
    # Reported as "B" or "S" here, unlike the live orders endpoint.
    side: str | None = None
    order_type: str | None = None
    order_status: str | None = None
    order_status_description: str | None = None
    order_ccp_status: str | None = None
    total_size: IbFloat = None
    size: IbFloat = None
    cum_fill: IbFloat = None
    average_price: IbFloat = None
    price: IbFloat = None
    stop_price: IbFloat = None
    tif: str | None = None
    outside_rth: bool | None = None
    order_time: str | None = None
    order_description: str | None = None
    order_description_with_contract: str | None = None
    cannot_cancel_order: bool | None = None
    order_not_editable: bool | None = None
    sub_type: str | None = None


class LiveOrder(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    order_id: IbInt = Field(default=None, alias="orderId")
    account: str | None = Field(default=None, alias="acct")
    conid: IbInt = None
    ticker: str | None = None
    company_name: str | None = Field(default=None, alias="companyName")
    sec_type: str | None = Field(default=None, alias="secType")
    listing_exchange: str | None = Field(default=None, alias="listingExchange")
    currency: str | None = Field(default=None, alias="cashCcy")
    # Reported as "BUY" or "SELL" here, unlike the order status endpoint.
    side: str | None = None
    status: str | None = None
    order_ccp_status: str | None = None
    order_type: str | None = Field(default=None, alias="orderType")
    orig_order_type: str | None = Field(default=None, alias="origOrderType")
    total_size: IbFloat = Field(default=None, alias="totalSize")
    filled_quantity: IbFloat = Field(default=None, alias="filledQuantity")
    remaining_quantity: IbFloat = Field(default=None, alias="remainingQuantity")
    avg_price: IbFloat = Field(default=None, alias="avgPrice")
    price: IbFloat = None
    stop_price: IbFloat = None
    time_in_force: str | None = Field(default=None, alias="timeInForce")
    # IB files the client order id sent as c_oid under this field.
    order_ref: str | None = None
    order_desc: str | None = Field(default=None, alias="orderDesc")
    size_and_fills: str | None = Field(default=None, alias="sizeAndFills")
    last_execution_time: str | None = Field(default=None, alias="lastExecutionTime")
    last_execution_time_r: IbInt = Field(default=None, alias="lastExecutionTime_r")


class Trade(BaseModel):
    # This endpoint already answers in snake_case, so aliases are only needed
    # for the handful of camelCase strays.
    model_config = ConfigDict(populate_by_name=True)

    execution_id: str | None = None
    symbol: str | None = None
    # Reported as "B" or "S", as on the order status endpoint.
    side: str | None = None
    order_description: str | None = None
    order_type: str | None = None
    trade_time: str | None = None
    trade_time_r: IbInt = None
    size: IbFloat = None
    price: IbFloat = None
    commission: IbFloat = None
    net_amount: IbFloat = None
    exchange: str | None = None
    # IB files the client order id sent as c_oid under this field.
    order_ref: str | None = None
    submitter: str | None = None
    account: str | None = None
    account_code: str | None = Field(default=None, alias="accountCode")
    company_name: str | None = None
    contract_description_1: str | None = None
    sec_type: str | None = None
    conid: IbInt = None
    position: IbFloat = None
    clearing_name: str | None = None
    liquidation_trade: str | None = None


class TransactionHistoryRequest(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True,
        populate_by_name=True,
    )

    # IB only honours a single contract id per call despite the plural field.
    acct_ids: list[str] = Field(alias="acctIds")
    conids: list[int]
    currency: str = "USD"
    # IB documents this as a string rather than a number.
    days: str | None = None


class Transaction(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    date: str | None = None
    currency: str | None = Field(default=None, alias="cur")
    price: IbFloat = Field(default=None, alias="pr")
    # Negative for sells, positive for buys.
    quantity: IbFloat = Field(default=None, alias="qty")
    amount: IbFloat = Field(default=None, alias="amt")
    conid: IbInt = None
    description: str | None = Field(default=None, alias="desc")
    type: str | None = None
    account_id: str | None = Field(default=None, alias="acctid")
    fx_rate_to_base: IbFloat = Field(default=None, alias="fxRateToBase")


class CancelOrderResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    order_id: IbInt = None
    conid: IbInt = None
    account: str | None = None
    msg: str | None = None
    error: str | None = None


class MarketDataSnapshot(BaseModel):
    # IB keys the quote fields by their numeric field code. Prices arrive as
    # strings and may carry a leading letter, so they are kept raw here and
    # parsed at the tool layer.
    model_config = ConfigDict(populate_by_name=True)

    conid: IbInt = None
    symbol: str | None = Field(default=None, alias="55")
    company_name: str | None = Field(default=None, alias="7051")
    last_price: str | None = Field(default=None, alias="31")
    bid_price: str | None = Field(default=None, alias="84")
    ask_price: str | None = Field(default=None, alias="86")
    ask_size: str | None = Field(default=None, alias="85")
    bid_size: str | None = Field(default=None, alias="88")
    open_price: str | None = Field(default=None, alias="7295")
    close_price: str | None = Field(default=None, alias="7296")
    volume: str | None = Field(default=None, alias="7762")
    availability: str | None = Field(default=None, alias="6509")
    updated: IbInt = Field(default=None, alias="_updated")


class SecurityInformation(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    con_id: int
    symbol: str
    currency: str
    company_name: str | None = None
    instrument_type: str | None = None
    exchange: str | None = None
    valid_exchanges: str | None = None
    trading_class: str | None = None
    industry: str | None = None
    category: str | None = None
    local_symbol: str | None = None
    cfi_code: str | None = None
    cusip: str | None = None
    expiry_full: str | None = None
    maturity_date: str | None = None
    contract_month: str | None = None
    multiplier: str | None = None
    underlying_con_id: int | None = None
    underlying_issuer: str | None = None
    contract_clarification_type: str | None = None
    classifier: str | None = None
    text: str | None = None
    allow_sell_long: bool = False
    is_zero_commission_security: bool = False
    smart_available: bool | None = None
    r_t_h: bool | None = None
