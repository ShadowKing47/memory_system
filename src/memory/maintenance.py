from contextlib import asynccontextmanager
from typing import Optional

from config import Settings, get_settings
from .database import Database
from .worker import DreamingWorker, ConsolidationStats
from .consolidation import ConsolidationResult
from .llm.client import OpenRouterClient
from .prompts.loader import PromptLoader
from .logging import get_logger

logger = get_logger(__name__)


class MemoryMaintenance:
    def __init__(
        self,
        db: Database,
        settings: Settings | None = None,
        llm_client: OpenRouterClient | None = None,
    ):
        self._db = db
        self._settings = settings or get_settings()
        self._llm_client = llm_client
        self._worker: DreamingWorker | None = None
    
    @asynccontextmanager
    async def worker(self):
        if self._worker is not None:
            raise RuntimeError("Worker already initialized")
        
        llm = self._llm_client or OpenRouterClient(self._settings.openrouter_api_key)
        self._worker = DreamingWorker(self._db, self._settings, llm)
        
        await self._worker.start()
        try:
            yield self._worker
        finally:
            await self._worker.stop()
            self._worker = None
    
    async def start_worker(self) -> DreamingWorker:
        if self._worker is not None:
            raise RuntimeError("Worker already running")
        
        llm = self._llm_client or OpenRouterClient(self._settings.openrouter_api_key)
        self._worker = DreamingWorker(self._db, self._settings, llm)
        await self._worker.start()
        return self._worker
    
    async def stop_worker(self):
        if self._worker is None:
            return
        await self._worker.stop()
        self._worker = None
    
    async def consolidate_once(
        self,
        session_id: Optional[str] = None,
    ) -> ConsolidationResult:
        llm = self._llm_client or OpenRouterClient(self._settings.openrouter_api_key)
        prompt_loader = PromptLoader(self._settings.prompts_dir)
        
        from .episodic import EpisodicRepository
        from .repository import MemoryRepository
        from .consolidation import consolidate_session
        
        return await consolidate_session(
            session_id=session_id or self._get_latest_session_id(),
            llm_client=llm,
            prompt_loader=prompt_loader,
            episodic_repo=EpisodicRepository(self._db.get_session()),
            semantic_repo=MemoryRepository(self._db.get_session()),
            batch_size=self._settings.dream_batch_size,
            prompt_version=self._settings.consolidation_prompt_version,
            min_messages=self._settings.dream_min_messages,
        )
    
    def _get_latest_session_id(self) -> str | None:
        from .episodic import create_episodic_repository
        with self._db.session() as session:
            repo = create_episodic_repository(session)
            session_ids = repo.get_session_ids(limit=1)
            return session_ids[0] if session_ids else None
    
    def get_worker_stats(self) -> ConsolidationStats | None:
        if self._worker is None:
            return None
        return self._worker.get_stats()
    
    @property
    def is_worker_running(self) -> bool:
        return self._worker is not None and self._worker.is_running