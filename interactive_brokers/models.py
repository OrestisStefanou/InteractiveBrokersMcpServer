import enum
from typing import TypeAlias

from pydantic import BaseModel, ConfigDict, Field, model_validator


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
