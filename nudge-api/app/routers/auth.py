from fastapi import APIRouter, Depends

from app.deps import get_auth_service
from app.schemas.auth import LoginRequest, LoginResponse
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, auth: AuthService = Depends(get_auth_service)):
    """Sign in as a student or teacher. `user.role` says which endpoints to use."""
    return auth.login(body.email, body.password)
