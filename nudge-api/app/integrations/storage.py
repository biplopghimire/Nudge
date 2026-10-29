"""File storage. The interface the services use, an in-memory mock, a
local-disk version for development, and Google Cloud Storage.
"""

from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import quote


class StorageClient(ABC):
    @abstractmethod
    def upload(self, path: str, data: bytes, content_type: str | None) -> None: ...

    @abstractmethod
    def download(self, path: str) -> bytes: ...

    @abstractmethod
    def copy(self, source_path: str, destination_path: str) -> None: ...

    @abstractmethod
    def signed_url(self, path: str, expires_in: timedelta) -> tuple[str, datetime]:
        """A temporary read link and when it expires."""


class MockStorage(StorageClient):
    """Keeps uploads in memory. Signed URLs look real but do not open anything."""

    def __init__(self, bucket: str):
        self.bucket = bucket
        self.files: dict[str, bytes] = {}

    def upload(self, path: str, data: bytes, content_type: str | None) -> None:
        self.files[path] = data

    def download(self, path: str) -> bytes:
        return self.files.get(path, b"")

    def copy(self, source_path: str, destination_path: str) -> None:
        if source_path in self.files:
            self.files[destination_path] = self.files[source_path]

    def signed_url(self, path: str, expires_in: timedelta) -> tuple[str, datetime]:
        expires_at = datetime.now(UTC) + expires_in
        url = (
            f"https://storage.googleapis.com/{self.bucket}/{quote(path)}"
            f"?X-Goog-Expires={int(expires_in.total_seconds())}&X-Goog-Signature=mock"
        )
        return url, expires_at


class LocalStorage(StorageClient):
    """Files on disk, for local development with a real database.

    Signed URLs point at http://localhost and are not served yet; real links
    come with cloud storage in step 2.
    """

    def __init__(self, root: str, bucket: str):
        self.root = Path(root).resolve()
        self.bucket = bucket

    def _file(self, path: str):
        target = (self.root / path).resolve()
        if not target.is_relative_to(self.root):
            raise ValueError(f"Path escapes storage root: {path}")
        return target

    def upload(self, path: str, data: bytes, content_type: str | None) -> None:
        target = self._file(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

    def download(self, path: str) -> bytes:
        target = self._file(path)
        return target.read_bytes() if target.exists() else b""

    def copy(self, source_path: str, destination_path: str) -> None:
        data = self.download(source_path)
        if data:
            self.upload(destination_path, data, None)

    def signed_url(self, path: str, expires_in: timedelta) -> tuple[str, datetime]:
        expires_at = datetime.now(UTC) + expires_in
        return f"http://localhost:8000/local-files/{quote(path)}?expires={int(expires_at.timestamp())}", expires_at


class GCSStorage(StorageClient):
    """Google Cloud Storage (Part 2): a private bucket, files reached only
    through 15-minute signed links.

    Credentials come from the environment (Cloud Run's service account, or
    `gcloud auth application-default login` locally). They act as
    `signer_email`, the backend's service account, so links are signed through
    the IAM API and no key file is ever downloaded.
    """

    SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]

    def __init__(self, bucket: str, signer_email: str | None):
        import google.auth
        from google.auth import impersonated_credentials
        from google.cloud import storage

        credentials, project = google.auth.default(scopes=self.SCOPES)
        if signer_email:
            credentials = impersonated_credentials.Credentials(
                source_credentials=credentials, target_principal=signer_email, target_scopes=self.SCOPES
            )
        self.credentials = credentials
        self.client = storage.Client(credentials=credentials, project=project)
        self.bucket = self.client.bucket(bucket)

    def upload(self, path: str, data: bytes, content_type: str | None) -> None:
        self.bucket.blob(path).upload_from_string(data, content_type=content_type or "application/octet-stream")

    def download(self, path: str) -> bytes:
        from google.api_core.exceptions import NotFound

        try:
            return self.bucket.blob(path).download_as_bytes()
        except NotFound:
            return b""

    def copy(self, source_path: str, destination_path: str) -> None:
        from google.api_core.exceptions import NotFound

        try:
            self.bucket.copy_blob(self.bucket.blob(source_path), self.bucket, destination_path)
        except NotFound:
            pass

    def signed_url(self, path: str, expires_in: timedelta) -> tuple[str, datetime]:
        url = self.bucket.blob(path).generate_signed_url(
            version="v4", expiration=expires_in, method="GET", credentials=self.credentials
        )
        return url, datetime.now(UTC) + expires_in
