import httpx
from pydantic import ValidationError

from interactive_brokers.errors import OrderResponseParseError
from interactive_brokers.models import (
    Account,
    PlaceOrderRequest,
    PlaceOrderResponse,
    Position,
    SearchContractRequest,
    SearchContractResult,
    SearchContractsResponse,
    SecurityInformation,
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
