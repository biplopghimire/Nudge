from app.schemas.common import CamelModel, UserOut


class LoginRequest(CamelModel):
    email: str
    password: str


class LoginResponse(CamelModel):
    token: str
    user: UserOut
