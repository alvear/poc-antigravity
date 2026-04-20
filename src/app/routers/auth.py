from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(tags=["auth"])

class AuthRequest(BaseModel):
    code: str
    redirect_uri: str

class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 28800

@router.post("/auth", response_model=AuthResponse)
async def authenticate(request: AuthRequest) -> AuthResponse:
    """
    Autentica usuario via Google OAuth 2.0.
    Troca authorization code por JWT token.
    """
    if not request.code:
        raise HTTPException(status_code=400, detail="Authorization code required")
    # TODO: integrar com Google Identity Platform
    return AuthResponse(access_token="jwt-token-placeholder")
