import enum

from pydantic import BaseModel


class SecurityType(enum.StrEnum):
    STOCK = "STOCK"
    INDEX = "INDEX"
    BOND = "BOND"


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
