"""TDD for Vercel Blob storage service — HTTP fully mocked (no network)."""
import asyncio

import pytest

import app.services.blob_storage_service as mod
from app.services.blob_storage_service import blob_storage_service


class _FakeResp:
    def __init__(self, status, json_data=None, text_data=""):
        self.status = status
        self._json = json_data or {}
        self._text = text_data
    async def json(self):
        return self._json
    async def text(self):
        return self._text
    async def __aenter__(self):
        return self
    async def __aexit__(self, *a):
        return False


class _FakeSession:
    def __init__(self, resp, capture):
        self._resp, self._capture = resp, capture
    def put(self, url, data=None, headers=None):
        self._capture.update(method="PUT", url=url, data=data, headers=headers)
        return self._resp
    def post(self, url, json=None, headers=None):
        self._capture.update(method="POST", url=url, json=json, headers=headers)
        return self._resp
    async def __aenter__(self):
        return self
    async def __aexit__(self, *a):
        return False


@pytest.fixture()
def token(monkeypatch):
    monkeypatch.setattr(mod.settings, "BLOB_READ_WRITE_TOKEN", "vercel_blob_rw_TESTSTORE_secret")


def test_upload_builds_url_headers_and_returns_public_url(monkeypatch, token):
    cap = {}
    public = "https://teststore.public.blob.vercel-storage.com/media-library/abc.png"
    resp = _FakeResp(200, {"url": public})
    monkeypatch.setattr(mod.aiohttp, "ClientSession", lambda *a, **k: _FakeSession(resp, cap))

    url = asyncio.run(
        blob_storage_service.upload_file_from_bytes(b"imagebytes", "media-library/abc.png", "image/png")
    )
    assert url == public
    assert cap["method"] == "PUT"
    assert cap["url"] == "https://blob.vercel-storage.com/media-library/abc.png"
    assert cap["data"] == b"imagebytes"
    assert cap["headers"]["authorization"] == "Bearer vercel_blob_rw_TESTSTORE_secret"
    assert cap["headers"]["x-content-type"] == "image/png"
    assert cap["headers"]["x-add-random-suffix"] == "0"


def test_delete_posts_url_to_delete_endpoint(monkeypatch, token):
    cap = {}
    resp = _FakeResp(200, {})
    monkeypatch.setattr(mod.aiohttp, "ClientSession", lambda *a, **k: _FakeSession(resp, cap))
    target = "https://teststore.public.blob.vercel-storage.com/media-library/abc.png"
    asyncio.run(blob_storage_service.delete_by_url(target))
    assert cap["method"] == "POST"
    assert cap["url"] == "https://blob.vercel-storage.com/delete"
    assert cap["json"] == {"urls": [target]}
    assert cap["headers"]["authorization"] == "Bearer vercel_blob_rw_TESTSTORE_secret"


def test_missing_token_raises(monkeypatch):
    monkeypatch.setattr(mod.settings, "BLOB_READ_WRITE_TOKEN", "")
    with pytest.raises(Exception):
        asyncio.run(blob_storage_service.upload_file_from_bytes(b"x", "k", "image/png"))
