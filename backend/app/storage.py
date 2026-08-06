"""
Supabase Storage client — persistent S3-compatible file storage.

Solves the critical Render ephemeral disk problem: uploaded PDFs/DOCXs
are no longer stored on the container's local filesystem (which gets wiped
on every deploy). Instead they are stored in a Supabase Storage bucket with
a permanent public URL.

Falls back to local filesystem gracefully if SUPABASE_URL / SUPABASE_SERVICE_KEY
env vars are not set (e.g. during local development).
"""
import os
import logging
from uuid import uuid4
from typing import Optional, Tuple

from .config import settings

logger = logging.getLogger("processpilot.storage")


class StorageClient:
    """
    Unified file storage client.
    Mode 1 — Supabase Storage: Activated when SUPABASE_URL + SUPABASE_SERVICE_KEY are set.
    Mode 2 — Local filesystem fallback: Used when env vars are missing (local dev).
    """

    def __init__(self):
        self._supabase = None
        self._use_supabase = bool(settings.SUPABASE_URL and settings.SUPABASE_KEY)

        if self._use_supabase:
            try:
                from supabase import create_client, Client
                self._supabase: Client = create_client(
                    settings.SUPABASE_URL,
                    settings.SUPABASE_KEY
                )
                logger.info(
                    f"[Storage] Supabase Storage initialised — bucket: '{settings.SUPABASE_STORAGE_BUCKET}'"
                )
            except ImportError:
                logger.warning(
                    "[Storage] 'supabase' package not installed. "
                    "Run: pip install supabase. Falling back to local disk."
                )
                self._use_supabase = False
            except Exception as e:
                logger.error(f"[Storage] Supabase init failed: {e}. Falling back to local disk.")
                self._use_supabase = False
        else:
            logger.info(
                "[Storage] SUPABASE_URL/SUPABASE_SERVICE_KEY not set — "
                "using local disk storage (⚠ ephemeral on Render)."
            )

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def upload(self, file_path: str, original_filename: str) -> Tuple[str, str]:
        """
        Upload a file and return (storage_path, public_url).

        storage_path — the unique object path inside the bucket (used to delete later).
        public_url   — the full URL where the file can be fetched for re-processing.

        If Supabase Storage is not configured, the file is saved to UPLOAD_DIR
        on the local filesystem and a file:// path is returned as the URL.
        """
        file_ext = original_filename.rsplit(".", 1)[-1].lower() if "." in original_filename else "bin"
        unique_name = f"{uuid4()}.{file_ext}"

        if self._use_supabase:
            return self._upload_supabase(file_path, unique_name)
        else:
            return self._upload_local(file_path, unique_name)

    def download(self, storage_path: str) -> bytes:
        """
        Download raw bytes for a previously-uploaded file by its storage_path.
        Used during background ingestion to retrieve file content after the
        HTTP request has already returned 202 Accepted.
        """
        if self._use_supabase:
            return self._download_supabase(storage_path)
        else:
            with open(storage_path, "rb") as f:
                return f.read()

    def delete(self, storage_path: str) -> None:
        """Delete a file from storage. Called when a Document record is deleted."""
        if self._use_supabase:
            try:
                self._supabase.storage.from_(settings.SUPABASE_STORAGE_BUCKET).remove([storage_path])
                logger.info(f"[Storage] Deleted from Supabase: {storage_path}")
            except Exception as e:
                logger.error(f"[Storage] Failed to delete {storage_path} from Supabase: {e}")
        else:
            try:
                if os.path.exists(storage_path):
                    os.remove(storage_path)
                    logger.info(f"[Storage] Deleted local file: {storage_path}")
            except Exception as e:
                logger.error(f"[Storage] Failed to delete local file {storage_path}: {e}")

    def is_supabase_enabled(self) -> bool:
        return self._use_supabase

    # ------------------------------------------------------------------ #
    #  Private: Supabase Storage backend                                  #
    # ------------------------------------------------------------------ #

    def _upload_supabase(self, file_path: str, unique_name: str) -> Tuple[str, str]:
        bucket = settings.SUPABASE_STORAGE_BUCKET
        storage_path = f"uploads/{unique_name}"

        try:
            with open(file_path, 'rb') as f:
                self._supabase.storage.from_(bucket).upload(
                    path=storage_path,
                    file=f,
                    file_options={"upsert": "true"}
                )
            # Build public URL (works for public buckets; for private buckets use signed URLs)
            public_url = (
                f"{settings.SUPABASE_URL}/storage/v1/object/public/{bucket}/{storage_path}"
            )
            logger.info(f"[Storage] Uploaded to Supabase: {storage_path}")
            return storage_path, public_url

        except Exception as e:
            logger.error(f"[Storage] Supabase upload failed: {e}. Falling back to local disk.")
            return self._upload_local(file_path, unique_name)

    def _download_supabase(self, storage_path: str) -> bytes:
        bucket = settings.SUPABASE_STORAGE_BUCKET
        try:
            response = self._supabase.storage.from_(bucket).download(storage_path)
            return response
        except Exception as e:
            raise RuntimeError(f"Failed to download {storage_path} from Supabase: {e}")

    # ------------------------------------------------------------------ #
    #  Private: Local filesystem fallback                                 #
    # ------------------------------------------------------------------ #

    def _upload_local(self, file_path: str, unique_name: str) -> Tuple[str, str]:
        import shutil
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        local_path = os.path.join(settings.UPLOAD_DIR, unique_name)
        if file_path != local_path:
            shutil.copy2(file_path, local_path)
        logger.info(f"[Storage] Saved to local disk: {local_path}")
        return local_path, f"file://{os.path.abspath(local_path)}"


# ---------------------------------------------------------------------------
# Module-level singleton — import this everywhere
# ---------------------------------------------------------------------------
storage_client = StorageClient()
