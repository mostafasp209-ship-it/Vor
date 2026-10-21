from pathlib import Path
from crypto_quant.knowledge import KnowledgeIndex

def test_index_ingests_and_returns_cited_local_chunks(tmp_path: Path):
    source = tmp_path / "notes.md"
    source.write_text("# Momentum research\nTime series momentum and trend following are studied in finance.", encoding="utf-8")
    index = KnowledgeIndex(tmp_path / "knowledge.sqlite3", chunk_chars=300, overlap=20)
    assert index.ingest_file(source) == 1
    hits = index.search("momentum trend")
    assert hits
    assert hits[0]["source_path"] == str(source.resolve())
    assert hits[0]["content_hash"]

def test_index_rejects_unsupported_file(tmp_path: Path):
    source = tmp_path / "book.pdf"
    source.write_bytes(b"not parsed")
    index = KnowledgeIndex(tmp_path / "knowledge.sqlite3")
    try:
        index.ingest_file(source)
    except ValueError as exc:
        assert ".txt and .md" in str(exc)
    else:
        raise AssertionError("PDF should not be silently accepted")
