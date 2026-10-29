import re

from app.domain import Role, User
from app.errors import ApiError, bad_request
from app.integrations.auth import AuthProvider
from app.repositories.base import Repository
from app.schemas.auth import LoginResponse
from app.schemas.common import UserOut
from app.services.common import new_id

EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD = 8
DEFAULT_NOTIFICATIONS = {
    "student": {"deadlineReminders": True, "studyNudges": True},
    "teacher": {"flaggedAnswers": True, "weeklyDigest": True},
}


def user_out(user: User) -> UserOut:
    return UserOut(id=user.id, name=user.name, email=user.email, role=user.role)


class AuthService:
    def __init__(self, repo: Repository, provider: AuthProvider):
        self.repo = repo
        self.provider = provider

    def login(self, email: str, password: str) -> LoginResponse:
        user = self.repo.get_user_by_email(email)
        password_hash = self.repo.get_password_hash(user.id) if user else None
        if not user or not self.provider.verify_password(password, password_hash):
            raise ApiError(401, "invalid_login", "That email and password don't match.")
        return LoginResponse(token=self.provider.issue_token(user), user=user_out(user))

    def signup(self, name: str, email: str, password: str, role: Role) -> LoginResponse:
        name, email = name.strip(), email.strip().lower()
        if not name:
            raise bad_request("missing_name", "Enter your name.")
        if len(name) > 100:
            raise bad_request("name_too_long", "Names can be up to 100 characters.")
        if not EMAIL.match(email):
            raise bad_request("invalid_email", "Enter a valid email address.")
        if len(password) < MIN_PASSWORD:
            raise bad_request("weak_password", f"Passwords need at least {MIN_PASSWORD} characters.")
        if self.repo.get_user_by_email(email):
            raise ApiError(409, "email_taken", "An account with that email already exists. Try signing in.")
        user = self.repo.create_user(
            User(id=new_id(), name=name, email=email, role=role, notifications=dict(DEFAULT_NOTIFICATIONS[role])),
            self.provider.hash_password(password),
        )
        return LoginResponse(token=self.provider.issue_token(user), user=user_out(user))

    def user_for_token(self, token: str | None) -> User:
        user_id = self.provider.user_id_from_token(token) if token else None
        user = self.repo.get_user(user_id) if user_id else None
        if not user:
            raise ApiError(401, "unauthorized", "Please sign in again.")
        return user
