from fastapi import APIRouter, Depends

from app.deps import get_auth_service
from app.schemas.auth import LoginRequest, LoginResponse, SignupRequest
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, auth: AuthService = Depends(get_auth_service)):
    """Sign in as a student or teacher. `user.role` says which endpoints to use."""
    return auth.login(body.email, body.password)


@router.post("/signup", response_model=LoginResponse, status_code=201)
def signup(body: SignupRequest, auth: AuthService = Depends(get_auth_service)):
    """Create a student or teacher account and sign in."""
    return auth.signup(body.name, body.email, body.password, body.role)
