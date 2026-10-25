"""Google Cloud Storage. The interface the services use, plus a mock.

The real version (GCSStorage) uses google-cloud-storage with the backend's
service account: blob.upload_from_string, blob.generate_signed_url(version="v4"),
bucket.copy_blob.
"""

from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta
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
