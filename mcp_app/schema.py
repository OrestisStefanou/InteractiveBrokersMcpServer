import enum

from pydantic import BaseModel, Field


class SecurityType(enum.StrEnum):
    STOCK = "STOCK"
    INDEX = "INDEX"
    BOND = "BOND"


class Account(BaseModel):
    id: str = Field(description="The account ID.")
    account_van: str | None = Field(default=None, description="The account alias.")
    account_title: str | None = Field(default=None, description="Title of the account.")
    display_name: str | None = Field(default=None, description="Display name of the account.")
    account_alias: str | None = Field(default=None, description="User customizable account alias.")
    account_status: int | None = Field(default=None, description="Unix timestamp of when the account was opened.")
    currency: str | None = Field(default=None, description="Base currency of the account.")
    type: str | None = Field(default=None, description="Account type (e.g. INDIVIDUAL, IRA, DEMO).")
    trading_type: str | None = Field(default=None, description="Account trading structure (e.g. PMRGN, STKCASH).")
    business_type: str | None = Field(default=None, description="Organizational structure of the account.")
    ib_entity: str | None = Field(default=None, description="Interactive Brokers entity the account is tied to.")
    fa_client: bool | None = Field(default=None, description="Whether the account is a sub-account of a Financial Advisor.")
    clearing_status: str | None = Field(default=None, description="Status of the account. O=Open, P/N=Pending, A=Abandoned, R=Rejected, C=Closed.")
    covestor: bool | None = Field(default=None, description="Whether this is a Covestor account.")
    no_client_trading: bool | None = Field(default=None, description="Whether the client account is restricted from trading.")
    track_virtual_fx_portfolio: bool | None = Field(default=None, description="Whether the account tracks a Virtual FX portfolio.")
    desc: str | None = Field(default=None, description="Account description in the format 'accountId - accountAlias'.")


class SecuritySearchResult(BaseModel):
    contract_id: str
    company_header: str
    company_name: str | None = None
    symbol: str | None = None
    description: str | None = None
    restricted: str | None = None
    bondid: int | None = None


class SecurityInformation(BaseModel):
    contract_id: int
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
