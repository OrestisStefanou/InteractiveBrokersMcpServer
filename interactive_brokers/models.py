import enum
from typing import TypeAlias

from pydantic import BaseModel, ConfigDict, Field


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
