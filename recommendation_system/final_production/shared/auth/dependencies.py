from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from shared.auth.jwt_handler import decode_token, extract_user_id

# FastAPI security scheme — enforces "Authorization: Bearer <token>" header
# and auto-documents it in Swagger UI (/docs) with a padlock icon.
_bearer_scheme = HTTPBearer()


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> str:
    """
    FastAPI dependency — extracts and validates the caller's user ID from the
    JWT Bearer token in the Authorization header.

    Usage in any route:
        async def my_endpoint(user_id: str = Depends(get_current_user_id)):
            ...

    Flow:
      1. FastAPI reads the 'Authorization: Bearer <token>' header.
      2. The token is decoded and fully verified (signature, expiry, issuer, audience).
      3. The user UUID is extracted from the 'sub' claim.
      4. The UUID is returned and injected directly into the route handler.

    Raises:
      HTTP 401 Unauthorized — missing header, invalid token, or expired token.
      HTTP 403 Forbidden    — token is valid but user ID claim is absent.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing or malformed.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = decode_token(token)
    return extract_user_id(payload)
