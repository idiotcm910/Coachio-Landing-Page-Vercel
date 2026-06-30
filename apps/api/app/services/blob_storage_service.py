"""Vercel Blob storage — media upload/delete layer (serverless-friendly).

Uploads PUT raw bytes to the Vercel Blob REST API
(`https://blob.vercel-storage.com/<pathname>`) authenticated with
BLOB_READ_WRITE_TOKEN; deletes POST the blob URL to `/delete`. Returns the public
CDN URL Vercel assigns. No SDK — plain aiohttp (already a dependency).
"""
import aiohttp

from app.core.config import settings

_BLOB_API_BASE = "https://blob.vercel-storage.com"
_BLOB_API_VERSION = "7"


class VercelBlobStorageService:
    """Upload/delete media via the Vercel Blob REST API."""

    def _auth_headers(self) -> dict:
        token = settings.BLOB_READ_WRITE_TOKEN
        if not token:
            raise Exception("BLOB_READ_WRITE_TOKEN is not configured")
        return {"authorization": f"Bearer {token}", "x-api-version": _BLOB_API_VERSION}

    async def upload_file_from_bytes(
        self, file_content: bytes, object_key: str, content_type: str | None = None
    ) -> str:
        """PUT bytes under `object_key` (used verbatim as the Blob pathname). Returns public URL."""
        url = f"{_BLOB_API_BASE}/{object_key.lstrip('/')}"
        headers = self._auth_headers()
        headers["x-add-random-suffix"] = "0"  # deterministic: pathname == object_key
        if content_type:
            headers["x-content-type"] = content_type
        async with aiohttp.ClientSession() as session:
            async with session.put(url, data=file_content, headers=headers) as resp:
                body = await resp.json()
                if resp.status != 200:
                    raise Exception(f"Vercel Blob upload failed ({resp.status}): {body}")
                return body["url"]

    async def delete_by_url(self, blob_url: str) -> None:
        """POST the blob URL to /delete. Idempotent — a missing URL is not an error."""
        headers = self._auth_headers()
        headers["content-type"] = "application/json"
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{_BLOB_API_BASE}/delete", json={"urls": [blob_url]}, headers=headers
            ) as resp:
                if resp.status not in (200, 204):
                    raise Exception(f"Vercel Blob delete failed ({resp.status}): {await resp.text()}")


blob_storage_service = VercelBlobStorageService()
