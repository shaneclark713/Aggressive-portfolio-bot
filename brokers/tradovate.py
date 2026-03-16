import aiohttp
from .models import OrderRequest

class TradovateClient:
    def __init__(self, base_url:str, ws_url:str, username:str, password:str, cid:str, secret:str, app_id:str, app_version:str, device_id:str, account_id:str):
        self.base_url=base_url.rstrip('/'); self.ws_url=ws_url; self.username=username; self.password=password; self.cid=cid; self.secret=secret; self.app_id=app_id; self.app_version=app_version; self.device_id=device_id; self.account_id=account_id; self.token=None; self.session=None; self.timeout=aiohttp.ClientTimeout(total=20)
    async def connect(self):
        if self.session is None or self.session.closed: self.session=aiohttp.ClientSession(timeout=self.timeout)
        await self.authenticate()
    async def close(self):
        if self.session and not self.session.closed: await self.session.close(); self.session=None; self.token=None
    async def authenticate(self):
        payload={'name':self.username,'password':self.password,'cid':self.cid,'sec':self.secret,'appId':self.app_id,'appVersion':self.app_version,'deviceId':self.device_id}
        async with self.session.post(f'{self.base_url}/auth/accesstokenrequest', json=payload) as r:
            r.raise_for_status(); data=await r.json(); self.token=data.get('accessToken')
            if not self.token: raise RuntimeError(f'Tradovate auth failed: {data}')
    def _headers(self): return {'Authorization': f'Bearer {self.token}'} if self.token else {}
    async def get_open_orders(self):
        async with self.session.get(f'{self.base_url}/order/list', headers=self._headers()) as r:
            r.raise_for_status(); data=await r.json(); return data if isinstance(data,list) else []
    async def place_order(self, req: OrderRequest):
        action='Buy' if req.side.upper()=='BUY' else 'Sell'; order_type={'market':'Market','limit':'Limit','stop':'Stop'}[req.order_type]
        payload={'accountId':int(self.account_id),'symbol':req.symbol,'action':action,'orderQty':req.quantity,'orderType':order_type,'isAutomated':True}
        if req.limit_price is not None: payload['limitPrice']=req.limit_price
        if req.stop_price is not None: payload['stopPrice']=req.stop_price
        async with self.session.post(f'{self.base_url}/order/placeorder', json=payload, headers=self._headers()) as r:
            r.raise_for_status(); return await r.json()
