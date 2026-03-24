"""Skeleton for ingesting evals from external 3rd-party sources."""
from abc import ABC, abstractmethod
from typing import Any


class NormalizedEval:
    """A normalized eval result ready for storage."""
    def __init__(
        self,
        benchmark_name: str,
        model_name: str,
        score: float,
        variant: str = "default",
        metric: str | None = None,
    ):
        self.benchmark_name = benchmark_name
        self.model_name = model_name
        self.score = score
        self.variant = variant
        self.metric = metric


class ExternalEvalIngester(ABC):
    """Base class for ingesting evals from external sources."""

    @abstractmethod
    async def fetch(self, source_config: dict) -> list[dict[str, Any]]:
        """Fetch raw eval data from the source. Override per source type."""
        ...

    @abstractmethod
    async def normalize(self, raw_data: list[dict[str, Any]]) -> list[NormalizedEval]:
        """Map raw data to our schema. Override per source type."""
        ...

    async def ingest(self, source_id: int, SessionLocal=None) -> int:
        """Full pipeline: fetch -> normalize -> match benchmarks -> store. Returns count."""
        # TODO: Implement when ready to activate external sources
        # 1. Load ExternalEvalSource config from DB
        # 2. Call self.fetch(config)
        # 3. Call self.normalize(raw_data)
        # 4. Match benchmark names to BenchmarkDefinition
        # 5. Match model names to ModelGeneration
        # 6. Create EvalResult rows with is_self_reported=False, source_type=source.slug
        # 7. Update source.last_fetched_at
        raise NotImplementedError("External ingestion not yet implemented")


class ArenaIngester(ExternalEvalIngester):
    """Ingest from LMSYS Chatbot Arena."""

    async def fetch(self, source_config: dict) -> list[dict[str, Any]]:
        # TODO: Fetch arena leaderboard data
        return []

    async def normalize(self, raw_data: list[dict[str, Any]]) -> list[NormalizedEval]:
        # TODO: Map arena format to NormalizedEval
        return []


class OpenLLMLeaderboardIngester(ExternalEvalIngester):
    """Ingest from HuggingFace Open LLM Leaderboard."""

    async def fetch(self, source_config: dict) -> list[dict[str, Any]]:
        # TODO: Scrape/fetch leaderboard data
        return []

    async def normalize(self, raw_data: list[dict[str, Any]]) -> list[NormalizedEval]:
        # TODO: Map leaderboard format to NormalizedEval
        return []
