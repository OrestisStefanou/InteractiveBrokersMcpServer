import enum

from pydantic import BaseModel


class SecurityType(enum.StrEnum):
    STOCK = "STK"
    INDEX = "IND"
    BOND = "BOND"


class SecuritySearchResult(BaseModel):
    conid: str
    company_header: str
    company_name: str | None = None
    symbol: str | None = None
    description: str | None = None
    restricted: str | None = None
    bondid: int | None = None
