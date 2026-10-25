from app.domain import User
from app.errors import ApiError
from app.integrations.auth import AuthProvider
from app.repositories.base import Repository
from app.schemas.auth import LoginResponse
from app.schemas.common import UserOut


def user_out(user: User) -> UserOut:
    return UserOut(id=user.id, name=user.name, email=user.email, role=user.role)


class AuthService:
    def __init__(self, repo: Repository, provider: AuthProvider):
        self.repo = repo
        self.provider = provider

    def login(self, email: str, password: str) -> LoginResponse:
        user = self.repo.get_user_by_email(email)
        if not user or not self.provider.check_password(user, password):
            raise ApiError(401, "invalid_login", "That email and password don't match.")
        return LoginResponse(token=self.provider.issue_token(user), user=user_out(user))

    def user_for_token(self, token: str | None) -> User:
        user_id = self.provider.user_id_from_token(token) if token else None
        user = self.repo.get_user(user_id) if user_id else None
        if not user:
            raise ApiError(401, "unauthorized", "Please sign in again.")
        return user
