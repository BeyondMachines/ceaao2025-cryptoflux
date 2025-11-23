from fastapi import Header, HTTPException
from .config import API_KEY

def enforce_api_key(x_api_key: str = Header(None)):
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="invalid api key")
