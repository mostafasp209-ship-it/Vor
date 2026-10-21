"""Research-capable trading specialist agents."""
from .registry import default_experts, get_expert
from .research_loop import ResearchAgent, ResearchNote, SearchResult
from .schema import ExpertOpinion

__all__ = ["ExpertOpinion", "ResearchAgent", "ResearchNote", "SearchResult", "default_experts", "get_expert"]

from .workflow import ExpertWorkflow
from .providers import ProviderError, brave_search, openai_compatible_chat

__all__ += ["ExpertWorkflow", "ProviderError", "brave_search", "openai_compatible_chat"]
