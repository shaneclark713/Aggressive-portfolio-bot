from __future__ import annotations

from services.options_chain_service import OptionsChainService


class OptionsDataService:
    def __init__(self, api_client):
        self.api = api_client
        self.chain_service = OptionsChainService()

    async def get_chain(self, symbol, expiration=None):
        chain = await self.api.get_options_chain(symbol=symbol, expiration=expiration)
        return chain

    def normalize(self, raw_chain, symbol=None):
        underlying = (symbol or "").upper() if symbol else "UNKNOWN"
        return self.chain_service.normalize_contracts(underlying, raw_chain)
