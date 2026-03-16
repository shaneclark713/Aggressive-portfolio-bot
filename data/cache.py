import time
class TTLCache:
    def __init__(self): self._data={}
    def get(self,key):
        item=self._data.get(key)
        if not item: return None
        exp,val=item
        if exp < time.time(): self._data.pop(key,None); return None
        return val
    def set(self,key,value,ttl_seconds:int): self._data[key]=(time.time()+ttl_seconds,value)
