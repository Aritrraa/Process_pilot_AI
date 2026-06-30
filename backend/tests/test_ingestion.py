"""
Ingestion pipeline tests — text chunking and file extraction.
"""
import pytest
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ingestion import chunk_text, extract_content, process_file_upload


class TestChunking:
    def test_empty_text_returns_empty(self):
        assert chunk_text("") == []

    def test_whitespace_only_returns_empty(self):
        assert chunk_text("   ") == []

    def test_none_returns_empty(self):
        assert chunk_text(None) == []

    def test_short_text_single_chunk(self):
        text = "Hello world, this is a short text."
        chunks = chunk_text(text, chunk_size=800)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_long_text_produces_multiple_chunks(self):
        text = "word " * 500  # ~2500 chars
        chunks = chunk_text(text, chunk_size=800)
        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk) <= 800

    def test_paragraph_splitting(self):
        text = "Paragraph one content here.\n\nParagraph two content here.\n\nParagraph three content here."
        chunks = chunk_text(text, chunk_size=50)
        assert len(chunks) >= 2

    def test_no_empty_chunks(self):
        text = "First sentence. Second sentence. Third sentence. " * 20
        chunks = chunk_text(text, chunk_size=100)
        for chunk in chunks:
            assert chunk.strip() != ""

    def test_very_long_word_handled(self):
        text = "a" * 2000  # Single 2000-char "word"
        chunks = chunk_text(text, chunk_size=800, chunk_overlap=150)
        assert len(chunks) >= 2

    def test_chunk_size_respected(self):
        text = "The quick brown fox jumps over the lazy dog. " * 100
        chunks = chunk_text(text, chunk_size=200)
        for chunk in chunks:
            assert len(chunk) <= 200

    def test_markdown_header_splitting(self):
        text = "# Title\n\nIntro paragraph.\n\n## Section 1\n\nContent one.\n\n## Section 2\n\nContent two."
        chunks = chunk_text(text, chunk_size=40)
        assert len(chunks) >= 2


class TestExtraction:
    def _write_temp(self, content, suffix):
        """Helper: write temp file, return path (caller must clean up)."""
        fd, path = tempfile.mkstemp(suffix=suffix)
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(content)
        return path

    def test_extract_txt_file(self):
        path = self._write_temp("Hello World Test Content", ".txt")
        try:
            result = extract_content(path, "txt")
            assert "Hello World" in result
        finally:
            os.unlink(path)

    def test_extract_csv_as_txt(self):
        path = self._write_temp("name,age\nAlice,30\nBob,25", ".csv")
        try:
            result = extract_content(path, "csv")
            assert "Alice" in result
        finally:
            os.unlink(path)

    def test_extract_nonexistent_file(self):
        result = extract_content("/nonexistent/file.txt", "txt")
        assert "error" in result.lower() or "Error" in result

    def test_extract_empty_file(self):
        path = self._write_temp("", ".txt")
        try:
            result = extract_content(path, "txt")
            assert result == ""
        finally:
            os.unlink(path)


class TestProcessUpload:
    def _write_temp(self, content, suffix):
        fd, path = tempfile.mkstemp(suffix=suffix)
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(content)
        return path

    def test_process_txt_file(self):
        path = self._write_temp("Test document content for processing and indexing.", ".txt")
        try:
            chunks = process_file_upload(path, "txt", document_id=1)
            assert len(chunks) >= 1
            assert chunks[0]["id"].startswith("doc_1_")
            assert "Test document" in chunks[0]["text"]
            assert chunks[0]["metadata"]["file_type"] == "txt"
        finally:
            os.unlink(path)

    def test_chunk_ids_are_sequential(self):
        path = self._write_temp("Long content. " * 200, ".txt")
        try:
            chunks = process_file_upload(path, "txt", document_id=5)
            for i, chunk in enumerate(chunks):
                assert chunk["id"] == f"doc_5_chunk_{i}"
                assert chunk["index"] == i
        finally:
            os.unlink(path)

    def test_metadata_has_filename(self):
        path = self._write_temp("Metadata test content", ".txt")
        try:
            chunks = process_file_upload(path, "txt", document_id=1)
            assert "file_name" in chunks[0]["metadata"]
        finally:
            os.unlink(path)
