import httpx
from pydantic import ValidationError

from interactive_brokers.errors import OrderResponseParseError
from interactive_brokers.models import (
    Account,
    AccountSummary,
    LedgerEntry,
    LiveOrder,
    OrderStatus,
    PlaceOrderRequest,
    PlaceOrderResponse,
    Position,
    SearchContractRequest,
    SearchContractResult,
    SearchContractsResponse,
    SecurityInformation,
    Trade,
    Transaction,
    TransactionHistoryRequest,
)


class InteractiveBrokersClient:
    def __init__(self, base_url: str) -> None:
        self._base_url = base_url

    async def search_contract(
        self,
        request: SearchContractRequest,
    ) -> SearchContractsResponse:
        url = f"{self._base_url}/iserver/secdef/search"

        query_params = request.model_dump(
            by_alias=True,
            exclude_none=True,
        )

        async with httpx.AsyncClient(verify=False) as client:
            response = await client.get(url, params=query_params)
            response.raise_for_status()
            data = response.json()

        return [SearchContractResult.model_validate(item) for item in data]

    async def get_accounts(self) -> list[Account]:
        url = f"{self._base_url}/portfolio/accounts"

        async with httpx.AsyncClient(verify=False) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

        return [Account.model_validate(item) for item in data]

    async def get_security_info_by_contract_id(
        self, contract_id: str
    ) -> SecurityInformation:
        url = f"{self._base_url}/iserver/contract/{contract_id}/info"

        async with httpx.AsyncClient(verify=False) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

        return SecurityInformation.model_validate(data)

    async def get_account_positions(
        self,
        account_id: str,
        sort: str | None = None,
        direction: str | None = None,
    ) -> list[Position]:
        url = f"{self._base_url}/portfolio2/{account_id}/positions"

        query_params = {}
        if sort is not None:
            query_params["sort"] = sort
        if direction is not None:
            query_params["direction"] = direction

        async with httpx.AsyncClient(verify=False) as client:
            response = await client.get(url, params=query_params)
            response.raise_for_status()
            data = response.json()

        return [Position.model_validate(item) for item in data]

    async def get_account_summary(self, account_id: str) -> AccountSummary:
        url = f"{self._base_url}/portfolio/{account_id}/summary"

        async with httpx.AsyncClient(verify=False) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

        return AccountSummary.model_validate(data)

    async def get_account_ledger(self, account_id: str) -> list[LedgerEntry]:
        url = f"{self._base_url}/portfolio/{account_id}/ledger"

        async with httpx.AsyncClient(verify=False) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

        # IB keys the ledger by currency code, using "BASE" for the account's
        # base currency. The key is the authoritative label, so prefer it over
        # the entry's own currency field.
        entries = []
        for currency, entry in data.items():
            if not isinstance(entry, dict):
                continue
            entries.append(LedgerEntry.model_validate({**entry, "currency": currency}))

        return entries

    async def get_order_status(self, order_id: str) -> OrderStatus:
        url = f"{self._base_url}/iserver/account/order/status/{order_id}"

        async with httpx.AsyncClient(verify=False) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

        return OrderStatus.model_validate(data)

    async def get_live_orders(
        self,
        account_id: str | None = None,
    ) -> list[LiveOrder]:
        url = f"{self._base_url}/iserver/account/orders"

        query_params = {}
        if account_id is not None:
            query_params["accountId"] = account_id

        async with httpx.AsyncClient(verify=False) as client:
            response = await client.get(url, params=query_params)
            response.raise_for_status()
            data = response.json()

        # IB wraps the orders in an envelope that also carries a snapshot flag
        # and notifications, and omits the key entirely when it has nothing to
        # report.
        orders = data.get("orders") or []

        return [LiveOrder.model_validate(item) for item in orders]

    async def get_trades(
        self,
        account_id: str | None = None,
        days: int | None = None,
    ) -> list[Trade]:
        url = f"{self._base_url}/iserver/account/trades"

        query_params = {}
        if account_id is not None:
            query_params["accountId"] = account_id
        if days is not None:
            query_params["days"] = str(days)

        async with httpx.AsyncClient(verify=False) as client:
            response = await client.get(url, params=query_params)
            response.raise_for_status()
            data = response.json()

        return [Trade.model_validate(item) for item in data]

    async def get_transaction_history(
        self,
        request: TransactionHistoryRequest,
    ) -> list[Transaction]:
        url = f"{self._base_url}/pa/transactions"

        payload = request.model_dump(by_alias=True, exclude_none=True)

        async with httpx.AsyncClient(verify=False) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

        # IB wraps the list in an envelope carrying the display currency and the
        # window covered, and omits the key entirely when it has nothing to
        # report.
        transactions = data.get("transactions") or []

        return [Transaction.model_validate(item) for item in transactions]

    async def place_order(
        self,
        account_id: str,
        order: PlaceOrderRequest,
    ) -> list[PlaceOrderResponse]:
        url = f"{self._base_url}/iserver/account/{account_id}/orders"

        order_body = order.model_dump(by_alias=True, exclude_none=True)
        payload = {"orders": [order_body]}

        async with httpx.AsyncClient(verify=False) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

        # The order is already placed on IB's side at this point. If IB's
        # response schema has drifted and parsing fails, surface a dedicated
        # error carrying the raw payload so the caller can reconcile rather
        # than mistaking a placed order for a failed one.
        try:
            return [PlaceOrderResponse.model_validate(item) for item in data]
        except ValidationError as exc:
            raise OrderResponseParseError(data) from exc

    async def confirm_order(
        self,
        reply_id: str,
        confirmed: bool = True,
    ) -> list[PlaceOrderResponse]:
        url = f"{self._base_url}/iserver/reply/{reply_id}"

        async with httpx.AsyncClient(verify=False) as client:
            response = await client.post(url, json={"confirmed": confirmed})
            response.raise_for_status()
            data = response.json()

        # Same reasoning as place_order: answering the reply may already have
        # released the order to the market, so a parse failure is "outcome
        # unknown", not "confirmation failed".
        try:
            return [PlaceOrderResponse.model_validate(item) for item in data]
        except ValidationError as exc:
            raise OrderResponseParseError(data) from exc
