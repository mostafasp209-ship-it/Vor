"""Persistent, deduplicated catalog for discovered scholarly records.

This stores bibliographic metadata and abstracts, not paper full text. It uses only
the Python standard library and deliberately preserves the evidence-level contract.
"""
from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


def _normalized_doi(value: str | None) -> str | None:
    if not value:
        return None
    doi = value.strip()
    doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi, flags=re.IGNORECASE)
    doi = re.sub(r"^doi:\s*", "", doi, flags=re.IGNORECASE).strip().lower()
    return doi or None


def _dedup_key(record: dict) -> str:
    doi = _normalized_doi(record.get("doi"))
    if doi:
        return "doi:" + doi
    title = re.sub(r"\s+", " ", (record.get("title") or "").strip().lower())
    year = str(record.get("year") or "")
    if title:
        return f"title-year:{title}|{year}"
    fallback = record.get("record_id") or record.get("work_id")
    if not fallback:
        raise ValueError("record needs a DOI, title, or stable record identifier")
    return "id:" + str(fallback)


class ResearchCatalog:
    """SQLite catalog for searchable scholarly metadata and evidence provenance."""

    def __init__(self, database_path: str | Path):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS research_records (
                    dedup_key TEXT PRIMARY KEY,
                    record_id TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    doi TEXT,
                    title TEXT NOT NULL DEFAULT '',
                    year INTEGER,
                    evidence_level TEXT NOT NULL CHECK(evidence_level IN ('metadata','abstract','full_text')),
                    full_text_ingested INTEGER NOT NULL DEFAULT 0 CHECK(full_text_ingested IN (0,1)),
                    retrieved_at TEXT,
                    record_json TEXT NOT NULL
                )
            """)
            db.execute("CREATE INDEX IF NOT EXISTS research_records_doi ON research_records(doi)")
            db.execute("CREATE INDEX IF NOT EXISTS research_records_year ON research_records(year)")

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.database_path)

    def upsert(self, records: Iterable[dict], retrieved_at: str | None = None) -> dict[str, int]:
        """Insert or refresh records; reject inconsistent full-text claims."""
        inserted = updated = skipped = 0
        with self._connect() as db:
            for original in records:
                record = dict(original)
                key = _dedup_key(record)
                record_id = str(record.get("record_id") or record.get("doi") or record.get("work_id") or key)
                source_id = str(record.get("source_id") or "unknown")
                title = str(record.get("title") or "")
                year = record.get("year")
                evidence = record.get("evidence_level") or ("abstract" if record.get("abstract") else "metadata")
                full_text = bool(record.get("full_text_ingested", False))
                if evidence not in {"metadata", "abstract", "full_text"}:
                    raise ValueError(f"unsupported evidence_level: {evidence}")
                if full_text != (evidence == "full_text"):
                    raise ValueError("full_text_ingested must be true exactly when evidence_level is full_text")
                if evidence == "full_text" and not record.get("license"):
                    raise ValueError("full-text records require a recorded license/authorization")
                if not title:
                    skipped += 1
                    continue
                if retrieved_at and not record.get("retrieved_at"):
                    record["retrieved_at"] = retrieved_at
                payload = json.dumps(record, ensure_ascii=False, sort_keys=True)
                existing = db.execute("SELECT 1 FROM research_records WHERE dedup_key=?", (key,)).fetchone()
                db.execute("""
                    INSERT INTO research_records
                    (dedup_key,record_id,source_id,doi,title,year,evidence_level,full_text_ingested,retrieved_at,record_json)
                    VALUES(?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(dedup_key) DO UPDATE SET
                        record_id=excluded.record_id, source_id=excluded.source_id,
                        doi=COALESCE(excluded.doi,research_records.doi),
                        title=excluded.title, year=COALESCE(excluded.year,research_records.year),
                        evidence_level=CASE
                            WHEN research_records.evidence_level='full_text' THEN 'full_text'
                            WHEN excluded.evidence_level='abstract' THEN 'abstract'
                            ELSE research_records.evidence_level END,
                        full_text_ingested=MAX(research_records.full_text_ingested,excluded.full_text_ingested),
                        retrieved_at=COALESCE(excluded.retrieved_at,research_records.retrieved_at),
                        record_json=CASE WHEN research_records.evidence_level='full_text' AND excluded.evidence_level!='full_text' THEN research_records.record_json ELSE excluded.record_json END
                """, (key, record_id, source_id, _normalized_doi(record.get("doi")), title, year,
                      evidence, int(full_text), record.get("retrieved_at"), payload))
                if existing:
                    updated += 1
                else:
                    inserted += 1
        return {"inserted": inserted, "updated": updated, "skipped": skipped}

    def search(self, query: str, limit: int = 10) -> list[dict]:
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        terms = [term.strip() for term in query.split() if term.strip()]
        if not terms:
            return []
        clauses = " AND ".join("(lower(title) LIKE ? OR lower(record_json) LIKE ?)" for _ in terms)
        args: list[object] = []
        for term in terms:
            needle = "%" + term.lower().replace("%", "\\%").replace("_", "\\_") + "%"
            args.extend((needle, needle))
        with self._connect() as db:
            rows = db.execute(
                f"SELECT record_json FROM research_records WHERE {clauses} ORDER BY "
                "CASE evidence_level WHEN 'full_text' THEN 0 WHEN 'abstract' THEN 1 ELSE 2 END, "
                "COALESCE(year,0) DESC LIMIT ?",
                (*args, limit),
            ).fetchall()
        return [json.loads(row[0]) for row in rows]

    def stats(self) -> dict[str, int]:
        with self._connect() as db:
            rows = db.execute("SELECT evidence_level, COUNT(*) FROM research_records GROUP BY evidence_level").fetchall()
            total = db.execute("SELECT COUNT(*) FROM research_records").fetchone()[0]
        result = {"total": total, "metadata": 0, "abstract": 0, "full_text": 0}
        result.update({level: count for level, count in rows})
        return result


def discover_openalex_into_catalog(catalog: ResearchCatalog, query: str, limit: int = 10, mailto: str | None = None) -> dict[str, object]:
    """Discover public OpenAlex metadata and persist it with a UTC retrieval timestamp."""
    from crypto_quant.knowledge.source_catalog import search_openalex
    records = search_openalex(query, limit=limit, mailto=mailto)
    retrieved_at = datetime.now(timezone.utc).isoformat()
    counts = catalog.upsert(records, retrieved_at=retrieved_at)
    return {"query": query, "retrieved_at": retrieved_at, "counts": counts, "records": records}
