from jose import jwt, JWTError
from fastapi import HTTPException, status

from shared.config.settings import settings

# ─────────────────────────────────────────────────────────────
# ASP.NET Identity claim names used by the Talentree main API
# ─────────────────────────────────────────────────────────────
_CLAIM_USER_ID = "sub"
_CLAIM_ROLE    = "http://schemas.microsoft.com/ws/2008/06/identity/claims/role"


def decode_token(token: str) -> dict:
    """
    Decodes and fully verifies a Talentree JWT Bearer token.

    Verifies:
      - Signature        (using the shared JWT_SECRET_KEY)
      - Algorithm        (must be HS256)
      - Expiry           (exp claim)
      - Issuer           (must be 'TalentreeApi')
      - Audience         (must be 'TalentreeClient')

    Raises:
      HTTP 401 Unauthorized — for any invalid, expired, or tampered token.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            audience=settings.JWT_AUDIENCE,
            issuer=settings.JWT_ISSUER,
        )
        return payload

    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token validation failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


def extract_user_id(payload: dict) -> str:
    """
    Extracts the user UUID from the 'sub' claim of the decoded JWT payload.

    Returns:
      The user's UUID string (e.g. '11111111-1111-1111-1111-111111111101').

    Raises:
      HTTP 401 Unauthorized — if the 'sub' claim is absent.
    """
    user_id = payload.get(_CLAIM_USER_ID)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID (sub) claim not found in token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return str(user_id)


def extract_role(payload: dict) -> str:
    """
    Extracts the user's role from the Microsoft role claim.

    Returns:
      Role string — e.g. 'BusinessOwner', 'Customer', or '' if not present.
    """
    return payload.get(_CLAIM_ROLE, "")
