from dataclasses import dataclass
from typing import Optional
@dataclass(slots=True)
class OrderRequest:
    trade_id:str; broker:str; symbol:str; side:str; instrument_type:str; quantity:int|float; order_type:str; limit_price:Optional[float]=None; stop_price:Optional[float]=None; option_right:Optional[str]=None; option_strike:Optional[float]=None; option_expiry:Optional[str]=None; notes:Optional[str]=None
