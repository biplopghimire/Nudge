from typing import Literal

from app.schemas.common import CamelModel, UserOut


class LoginRequest(CamelModel):
    email: str
    password: str


class LoginResponse(CamelModel):
    token: str
    user: UserOut


class SignupRequest(CamelModel):
    name: str
    email: str
    password: str
    role: Literal["student", "teacher"]
