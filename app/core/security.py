# app/core/security.py
import os
from fastapi import Depends, HTTPException, status
from fastapi.security.api_key import APIKeyHeader

ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "")
_api_key_header = APIKeyHeader(name="x-admin-key", auto_error=False)

def require_admin(api_key: str = Depends(_api_key_header)) -> None:
    if not ADMIN_API_KEY or api_key != ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing admin key",
        )
