"""Local document ingestion and retrieval for licensed/open research sources."""
from .index import KnowledgeIndex, DocumentChunk
from .research_store import ResearchCatalog, discover_openalex_into_catalog
from .evaluation import evaluate_retrieval
__all__ = ["KnowledgeIndex", "DocumentChunk", "ResearchCatalog", "discover_openalex_into_catalog", "evaluate_retrieval"]
