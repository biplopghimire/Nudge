"""Passwords and login tokens. The interface the services use, a mock, and the
real version (JWTAuthProvider).
"""

import base64
import hashlib
import hmac
import secrets
from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta

import jwt

from app.domain import User


class AuthProvider(ABC):
    @abstractmethod
    def hash_password(self, password: str) -> str: ...

    @abstractmethod
    def verify_password(self, password: str, password_hash: str | None) -> bool: ...

    @abstractmethod
    def issue_token(self, user: User) -> str: ...

    @abstractmethod
    def user_id_from_token(self, token: str) -> str | None:
        """The user id the token belongs to, or None if it is invalid or expired."""


class MockAuthProvider(AuthProvider):
    """Any non-empty password works. Tokens are 'mock-{userId}'."""

    PREFIX = "mock-"

    def hash_password(self, password: str) -> str:
        return "mock"

    def verify_password(self, password: str, password_hash: str | None) -> bool:
        return bool(password)

    def issue_token(self, user: User) -> str:
        return f"{self.PREFIX}{user.id}"

    def user_id_from_token(self, token: str) -> str | None:
        return token.removeprefix(self.PREFIX) if token.startswith(self.PREFIX) else None


class JWTAuthProvider(AuthProvider):
    """scrypt password hashes and HS256-signed tokens whose subject is the user id."""

    N, R, P = 2**14, 8, 1

    def __init__(self, secret: str, token_days: int = 30):
        if len(secret) < 32:
            raise ValueError("The token secret must be at least 32 characters.")
        self.secret = secret
        self.lifetime = timedelta(days=token_days)

    def _scrypt(self, password: str, salt: bytes, n: int, r: int, p: int) -> bytes:
        return hashlib.scrypt(password.encode(), salt=salt, n=n, r=r, p=p, dklen=32)

    def hash_password(self, password: str) -> str:
        salt = secrets.token_bytes(16)
        digest = self._scrypt(password, salt, self.N, self.R, self.P)
        encode = lambda b: base64.b64encode(b).decode()  # noqa: E731
        return f"scrypt${self.N}${self.R}${self.P}${encode(salt)}${encode(digest)}"

    def verify_password(self, password: str, password_hash: str | None) -> bool:
        try:
            scheme, n, r, p, salt, digest = (password_hash or "").split("$")
        except ValueError:
            return False
        if scheme != "scrypt":
            return False
        actual = self._scrypt(password, base64.b64decode(salt), int(n), int(r), int(p))
        return hmac.compare_digest(actual, base64.b64decode(digest))

    def issue_token(self, user: User) -> str:
        now = datetime.now(UTC)
        claims = {"sub": user.id, "role": user.role, "iat": now, "exp": now + self.lifetime}
        return jwt.encode(claims, self.secret, algorithm="HS256")

    def user_id_from_token(self, token: str) -> str | None:
        try:
            return jwt.decode(token, self.secret, algorithms=["HS256"], options={"require": ["sub", "exp"]})["sub"]
        except jwt.PyJWTError:
            return None
