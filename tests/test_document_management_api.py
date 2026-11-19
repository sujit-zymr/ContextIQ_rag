"""Tests for the Document Management API endpoints.

Tests are written with unittest + FastAPI TestClient so they run without a
running server.  Database calls and file I/O are mocked so the suite remains
fast and self-contained.

Covered endpoints:
    GET  /documents
    GET  /documents/{document_id}
    POST /documents/upload
    DELETE /documents/{document_id}
"""

import io
import unittest
import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

FAKE_USER = {
    "id": uuid.UUID("00000000-0000-0000-0000-000000000001"),
    "email": "test@example.com",
    "created_at": datetime(2026, 1, 1),
}

DOC_ID = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000001")

FAKE_DOC_SUMMARY = {
    "id": DOC_ID,
    "filename": "policy.pdf",
    "status": "completed",
    "status_message": None,
    "metadata": {"title": "Policy", "file_type": "pdf"},
    "created_at": datetime(2026, 1, 1),
    "updated_at": datetime(2026, 1, 2),
    "chunk_count": 10,
}

FAKE_DOC_DETAIL = {
    **FAKE_DOC_SUMMARY,
    "file_hash": "deadbeef" * 8,
    "source_path": "/storage/uploads/policy.pdf",
    "total_chars": 5000,
}

FAKE_DOC_BASIC = {
    "id": DOC_ID,
    "filename": "policy.pdf",
    "file_hash": "deadbeef" * 8,
    "source_path": "/storage/uploads/policy.pdf",
    "metadata": {"title": "Policy", "file_type": "pdf"},
    "status": "completed",
}


def _make_client():
    """Build a TestClient with the JWT auth dependency overridden."""
    from app.api.main import app
    from app.api.auth import get_current_user

    app.dependency_overrides[get_current_user] = lambda: FAKE_USER
    client = TestClient(app, raise_server_exceptions=True)
    return client, app


# ---------------------------------------------------------------------------
# GET /documents
# ---------------------------------------------------------------------------

class TestListDocuments(unittest.TestCase):

    @patch("app.api.documents.count_documents", return_value=1)
    @patch("app.api.documents.list_documents", return_value=[FAKE_DOC_SUMMARY])
    @patch("app.api.documents.observation_span")
    def test_list_returns_paginated_response(self, mock_span, mock_list, mock_count):
        mock_span.return_value.__enter__ = lambda s: MagicMock()
        mock_span.return_value.__exit__ = MagicMock(return_value=False)

        client, app = _make_client()
        response = client.get("/documents")
        app.dependency_overrides.clear()

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["total"], 1)
        self.assertEqual(body["limit"], 50)
        self.assertEqual(body["offset"], 0)
        self.assertEqual(len(body["items"]), 1)
        self.assertEqual(body["items"][0]["filename"], "policy.pdf")
        self.assertEqual(body["items"][0]["chunk_count"], 10)

    @patch("app.api.documents.count_documents", return_value=0)
    @patch("app.api.documents.list_documents", return_value=[])
    @patch("app.api.documents.observation_span")
    def test_list_empty_knowledge_base(self, mock_span, mock_list, mock_count):
        mock_span.return_value.__enter__ = lambda s: MagicMock()
        mock_span.return_value.__exit__ = MagicMock(return_value=False)

        client, app = _make_client()
        response = client.get("/documents")
        app.dependency_overrides.clear()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total"], 0)
        self.assertEqual(response.json()["items"], [])

    @patch("app.api.documents.count_documents", return_value=1)
    @patch("app.api.documents.list_documents", return_value=[FAKE_DOC_SUMMARY])
    @patch("app.api.documents.observation_span")
    def test_list_with_status_filter(self, mock_span, mock_list, mock_count):
        mock_span.return_value.__enter__ = lambda s: MagicMock()
        mock_span.return_value.__exit__ = MagicMock(return_value=False)

        client, app = _make_client()
        response = client.get("/documents?status=completed")
        app.dependency_overrides.clear()

        self.assertEqual(response.status_code, 200)
        mock_list.assert_called_once_with(status="completed", limit=50, offset=0)

    @patch("app.api.documents.count_documents", return_value=5)
    @patch("app.api.documents.list_documents", return_value=[FAKE_DOC_SUMMARY])
    @patch("app.api.documents.observation_span")
    def test_list_with_pagination(self, mock_span, mock_list, mock_count):
        mock_span.return_value.__enter__ = lambda s: MagicMock()
        mock_span.return_value.__exit__ = MagicMock(return_value=False)

        client, app = _make_client()
        response = client.get("/documents?limit=1&offset=2")
        app.dependency_overrides.clear()

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["limit"], 1)
        self.assertEqual(body["offset"], 2)
        self.assertEqual(body["total"], 5)
        mock_list.assert_called_once_with(status=None, limit=1, offset=2)

    def test_list_requires_auth(self):
        from app.api.main import app
        # No dependency override – use a fresh client without auth
        client = TestClient(app, raise_server_exceptions=True)
        response = client.get("/documents")
        self.assertEqual(response.status_code, 401)


# ---------------------------------------------------------------------------
# GET /documents/{document_id}
# ---------------------------------------------------------------------------

class TestGetDocument(unittest.TestCase):

    @patch("app.api.documents.get_document_detail", return_value=FAKE_DOC_DETAIL)
    @patch("app.api.documents.observation_span")
    def test_get_existing_document(self, mock_span, mock_detail):
        mock_span.return_value.__enter__ = lambda s: MagicMock()
        mock_span.return_value.__exit__ = MagicMock(return_value=False)

        client, app = _make_client()
        response = client.get(f"/documents/{DOC_ID}")
        app.dependency_overrides.clear()

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["id"], str(DOC_ID))
        self.assertEqual(body["filename"], "policy.pdf")
        self.assertEqual(body["chunk_count"], 10)
        self.assertEqual(body["total_chars"], 5000)

    @patch("app.api.documents.get_document_detail", return_value=None)
    @patch("app.api.documents.observation_span")
    def test_get_nonexistent_document_returns_404(self, mock_span, mock_detail):
        mock_span.return_value.__enter__ = lambda s: MagicMock()
        mock_span.return_value.__exit__ = MagicMock(return_value=False)

        client, app = _make_client()
        response = client.get(f"/documents/{DOC_ID}")
        app.dependency_overrides.clear()

        self.assertEqual(response.status_code, 404)
        self.assertIn("not found", response.json()["detail"].lower())

    def test_get_requires_auth(self):
        from app.api.main import app
        client = TestClient(app, raise_server_exceptions=True)
        response = client.get(f"/documents/{DOC_ID}")
        self.assertEqual(response.status_code, 401)


# ---------------------------------------------------------------------------
# POST /documents/upload
# ---------------------------------------------------------------------------

class TestUploadDocument(unittest.TestCase):

    def _upload(self, client, filename="test.pdf", content=b"%PDF-1.4 test content"):
        return client.post(
            "/documents/upload",
            files={"file": (filename, io.BytesIO(content), "application/octet-stream")},
        )

    @patch("app.api.documents.get_document_detail", return_value={**FAKE_DOC_DETAIL, "chunk_count": 7})
    @patch("app.api.documents.get_document", return_value=FAKE_DOC_BASIC)
    @patch("app.api.documents.ingest_file", return_value=DOC_ID)
    @patch("app.api.documents._resolve_upload_dir")
    @patch("app.api.documents.observation_span")
    def test_upload_valid_pdf(self, mock_span, mock_dir, mock_ingest, mock_get, mock_detail):
        import tempfile, pathlib
        tmp = pathlib.Path(tempfile.mkdtemp())
        mock_dir.return_value = tmp
        mock_span.return_value.__enter__ = lambda s: MagicMock()
        mock_span.return_value.__exit__ = MagicMock(return_value=False)

        client, app = _make_client()
        response = self._upload(client, "test.pdf")
        app.dependency_overrides.clear()

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["document_id"], str(DOC_ID))
        self.assertEqual(body["filename"], "test.pdf")
        self.assertEqual(body["status"], "completed")
        self.assertEqual(body["chunk_count"], 7)
        self.assertIn("successfully", body["message"])

    @patch("app.api.documents.observation_span")
    def test_upload_unsupported_extension_returns_422(self, mock_span):
        mock_span.return_value.__enter__ = lambda s: MagicMock()
        mock_span.return_value.__exit__ = MagicMock(return_value=False)

        client, app = _make_client()
        response = self._upload(client, "image.png", b"\x89PNG")
        app.dependency_overrides.clear()

        self.assertEqual(response.status_code, 422)
        self.assertIn(".png", response.json()["detail"])

    @patch("app.api.documents.observation_span")
    def test_upload_empty_file_returns_422(self, mock_span):
        mock_span.return_value.__enter__ = lambda s: MagicMock()
        mock_span.return_value.__exit__ = MagicMock(return_value=False)

        client, app = _make_client()
        response = self._upload(client, "empty.txt", b"")
        app.dependency_overrides.clear()

        self.assertEqual(response.status_code, 422)
        self.assertIn("empty", response.json()["detail"].lower())

    @patch("app.api.documents.get_document_detail", return_value={**FAKE_DOC_DETAIL, "chunk_count": 5})
    @patch("app.api.documents.get_document", return_value=FAKE_DOC_BASIC)
    @patch("app.api.documents.ingest_file", return_value=DOC_ID)
    @patch("app.api.documents._resolve_upload_dir")
    @patch("app.api.documents.observation_span")
    def test_upload_txt_file(self, mock_span, mock_dir, mock_ingest, mock_get, mock_detail):
        import tempfile, pathlib
        tmp = pathlib.Path(tempfile.mkdtemp())
        mock_dir.return_value = tmp
        mock_span.return_value.__enter__ = lambda s: MagicMock()
        mock_span.return_value.__exit__ = MagicMock(return_value=False)

        client, app = _make_client()
        response = self._upload(client, "notes.txt", b"Some text content here.")
        app.dependency_overrides.clear()

        self.assertEqual(response.status_code, 201)

    @patch("app.api.documents._resolve_upload_dir")
    @patch("app.api.documents.observation_span")
    def test_upload_ingestion_error_returns_422(self, mock_span, mock_dir):
        import tempfile, pathlib
        tmp = pathlib.Path(tempfile.mkdtemp())
        mock_dir.return_value = tmp
        mock_span.return_value.__enter__ = lambda s: MagicMock()
        mock_span.return_value.__exit__ = MagicMock(return_value=False)

        with patch("app.api.documents.ingest_file", side_effect=ValueError("Document contains no readable text")):
            client, app = _make_client()
            response = self._upload(client, "blank.pdf", b"%PDF-blank")
            app.dependency_overrides.clear()

        self.assertEqual(response.status_code, 422)
        self.assertIn("no readable text", response.json()["detail"])

    def test_upload_requires_auth(self):
        from app.api.main import app
        client = TestClient(app, raise_server_exceptions=True)
        response = client.post(
            "/documents/upload",
            files={"file": ("test.pdf", io.BytesIO(b"%PDF-test"), "application/pdf")},
        )
        self.assertEqual(response.status_code, 401)


# ---------------------------------------------------------------------------
# DELETE /documents/{document_id}
# ---------------------------------------------------------------------------

class TestDeleteDocument(unittest.TestCase):

    @patch("app.api.documents.delete_document", return_value=True)
    @patch("app.api.documents.get_document", return_value=FAKE_DOC_BASIC)
    @patch("app.api.documents.observation_span")
    def test_delete_existing_document(self, mock_span, mock_get, mock_delete):
        mock_span.return_value.__enter__ = lambda s: MagicMock()
        mock_span.return_value.__exit__ = MagicMock(return_value=False)

        client, app = _make_client()
        response = client.delete(f"/documents/{DOC_ID}")
        app.dependency_overrides.clear()

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["document_id"], str(DOC_ID))
        self.assertTrue(body["deleted"])
        self.assertIn("removed", body["message"])

    @patch("app.api.documents.get_document", return_value=None)
    @patch("app.api.documents.observation_span")
    def test_delete_nonexistent_document_returns_404(self, mock_span, mock_get):
        mock_span.return_value.__enter__ = lambda s: MagicMock()
        mock_span.return_value.__exit__ = MagicMock(return_value=False)

        client, app = _make_client()
        response = client.delete(f"/documents/{DOC_ID}")
        app.dependency_overrides.clear()

        self.assertEqual(response.status_code, 404)
        self.assertIn("not found", response.json()["detail"].lower())

    def test_delete_requires_auth(self):
        from app.api.main import app
        client = TestClient(app, raise_server_exceptions=True)
        response = client.delete(f"/documents/{DOC_ID}")
        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
