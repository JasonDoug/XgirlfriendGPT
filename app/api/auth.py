from fastapi import APIRouter, HTTPException, status, Header, Depends
from pydantic import BaseModel
from typing import Optional
from app.services.auth_service import create_access_token, verify_access_token

router = APIRouter(prefix="/auth", tags=["Authentication & Multi-User"])

class TokenRequest(BaseModel):
    user_id: str
    password: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    expires_in: int = 86400

@router.post("/token", response_model=TokenResponse)
def login_for_access_token(req: TokenRequest):
    """
    Issues JWT access token for an authenticated user account.
    """
    if not req.user_id or not isinstance(req.user_id, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Valid user_id is required"
        )
    user_id = req.user_id.strip()
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id cannot be empty or blank"
        )
    token = create_access_token(user_id=user_id)
    return TokenResponse(access_token=token, user_id=user_id)

@router.get("/me")
def get_current_user(authorization: Optional[str] = Header(None)):
    """
    Returns authenticated user info from Authorization: Bearer <token> header.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header"
        )
    token = authorization.split(" ", 1)[1]
    payload = verify_access_token(token)
    return {"user_id": payload.get("sub"), "issued_at": payload.get("iat")}
