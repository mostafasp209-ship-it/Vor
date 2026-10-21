"""Dependency-free SQLite FTS knowledge index with source provenance.
Only index documents you are legally allowed to store. Initial formats: .txt and .md.
"""
from dataclasses import dataclass
from pathlib import Path
import hashlib
import sqlite3

@dataclass(frozen=True)
class DocumentChunk:
    source_path: str
    title: str
    chunk_id: str
    text: str
    content_hash: str

class KnowledgeIndex:
    def __init__(self, database_path: str | Path, chunk_chars: int = 1400, overlap: int = 180):
        if chunk_chars < 200 or overlap < 0 or overlap >= chunk_chars:
            raise ValueError("Require chunk_chars >= 200 and 0 <= overlap < chunk_chars")
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.chunk_chars, self.overlap = chunk_chars, overlap
        with self._connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS chunks (source_path TEXT NOT NULL, title TEXT NOT NULL, chunk_id TEXT NOT NULL, text TEXT NOT NULL, content_hash TEXT NOT NULL, PRIMARY KEY(source_path, chunk_id))")
            db.execute("CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(title, text, content='chunks', content_rowid='rowid')")
            db.executescript("""CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN INSERT INTO chunks_fts(rowid,title,text) VALUES(new.rowid,new.title,new.text); END;
            CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN INSERT INTO chunks_fts(chunks_fts,rowid,title,text) VALUES('delete',old.rowid,old.title,old.text); END;
            CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON chunks BEGIN INSERT INTO chunks_fts(chunks_fts,rowid,title,text) VALUES('delete',old.rowid,old.title,old.text); INSERT INTO chunks_fts(rowid,title,text) VALUES(new.rowid,new.title,new.text); END;""")
    def _connect(self):
        return sqlite3.connect(self.database_path)
    def ingest_file(self, path: str | Path) -> int:
        path = Path(path).resolve()
        if path.suffix.lower() not in {".txt", ".md"}:
            raise ValueError("Only .txt and .md are supported by this prototype")
        raw = path.read_text(encoding="utf-8")
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        title = next((line.lstrip("# ").strip() for line in raw.splitlines() if line.strip()), path.stem)
        step = self.chunk_chars - self.overlap
        chunks = [raw[i:i + self.chunk_chars].strip() for i in range(0, len(raw), step)]
        chunks = [chunk for chunk in chunks if chunk]
        with self._connect() as db:
            db.execute("DELETE FROM chunks WHERE source_path=?", (str(path),))
            db.executemany("INSERT INTO chunks(source_path,title,chunk_id,text,content_hash) VALUES(?,?,?,?,?)", [(str(path), title, str(i), chunk, digest) for i, chunk in enumerate(chunks)])
        return len(chunks)
    def ingest_directory(self, directory: str | Path) -> dict[str, int]:
        report = {}
        for path in sorted(Path(directory).rglob("*")):
            if path.is_file() and path.suffix.lower() in {".txt", ".md"}:
                report[str(path)] = self.ingest_file(path)
        return report
    def search(self, query: str, limit: int = 5) -> list[dict]:
        if not query.strip():
            return []
        if not 1 <= limit <= 50:
            raise ValueError("limit must be between 1 and 50")
        terms = [term.replace('"', '""') for term in query.split() if term]
        match_query = " AND ".join(f'"{term}"' for term in terms)
        with self._connect() as db:
            rows = db.execute("SELECT c.source_path,c.title,c.chunk_id,c.text,c.content_hash FROM chunks_fts f JOIN chunks c ON c.rowid=f.rowid WHERE chunks_fts MATCH ? ORDER BY bm25(chunks_fts) LIMIT ?", (match_query, limit)).fetchall()
        return [{"source_path": r[0], "title": r[1], "chunk_id": r[2], "text": r[3], "content_hash": r[4]} for r in rows]
