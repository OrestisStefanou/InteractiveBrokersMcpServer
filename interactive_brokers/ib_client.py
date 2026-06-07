import httpx

from interactive_brokers.models import (
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

    async def get_security_info_by_contract_id(
        self, contract_id: str
    ) -> SecurityInformation:
        url = f"{self._base_url}/iserver/contract/{contract_id}/info"

        async with httpx.AsyncClient(verify=False) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

        return SecurityInformation.model_validate(data)
