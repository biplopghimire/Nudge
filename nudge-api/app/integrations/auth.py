"""Login and tokens. The interface the services use, plus a mock.

The real version should check a password hash (or hand off to Supabase Auth)
and issue signed JWTs whose subject is the user id.
"""

from abc import ABC, abstractmethod

from app.domain import User


class AuthProvider(ABC):
    @abstractmethod
    def check_password(self, user: User, password: str) -> bool: ...

    @abstractmethod
    def issue_token(self, user: User) -> str: ...

    @abstractmethod
    def user_id_from_token(self, token: str) -> str | None:
        """The user id the token belongs to, or None if it is invalid or expired."""


class MockAuthProvider(AuthProvider):
    """Any non-empty password works. Tokens are 'mock-{userId}'."""

    PREFIX = "mock-"

    def check_password(self, user: User, password: str) -> bool:
        return bool(password)

    def issue_token(self, user: User) -> str:
        return f"{self.PREFIX}{user.id}"

    def user_id_from_token(self, token: str) -> str | None:
        return token.removeprefix(self.PREFIX) if token.startswith(self.PREFIX) else None
