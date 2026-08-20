import asyncio
import logging
from dataclasses import dataclass, field
from typing import Optional

from config import Settings
from .database import Database
from .llm.client import OpenRouterClient
from .llm.protocol import LLMClientProtocol
from .prompts.loader import PromptLoader
from .consolidation import ConsolidationResult, consolidate_session
from .episodic import EpisodicRepository, create_episodic_repository
from .repository import MemoryRepository, create_repository
from .logging import get_logger

logger = get_logger(__name__)


@dataclass
class ConsolidationStats:
    total_runs: int = 0
    total_facts_extracted: int = 0
    total_facts_upserted: int = 0
    total_facts_superseded: int = 0
    total_errors: int = 0
    last_run_duration_ms: int = 0
    last_run_session: str | None = None
    last_error: str | None = None
    
    def record_result(self, result: ConsolidationResult, session_id: str):
        self.total_runs += 1
        self.total_facts_extracted += result.facts_extracted
        self.total_facts_upserted += result.facts_upserted
        self.total_facts_superseded += result.facts_superseded
        self.last_run_duration_ms = result.duration_ms
        self.last_run_session = session_id
        if result.errors:
            self.total_errors += len(result.errors)
            self.last_error = result.errors[-1]
        else:
            self.last_error = None
    
    def record_error(self):
        self.total_errors += 1


class DreamingWorker:
    def __init__(
        self,
        db: Database,
        settings: Settings,
        llm_client: LLMClientProtocol | None = None,
        prompt_loader: PromptLoader | None = None,
    ):
        self._db = db
        self._settings = settings
        self._llm_client = llm_client or OpenRouterClient(settings.openrouter_api_key)
        self._prompt_loader = prompt_loader or PromptLoader(settings.prompts_dir)
        self._task: asyncio.Task | None = None
        self._shutdown = asyncio.Event()
        self._stats = ConsolidationStats()
        self._own_llm_client = llm_client is None
    
    async def start(self):
        if self._task is not None:
            logger.warning("worker_already_running")
            return
        self._shutdown.clear()
        self._task = asyncio.create_task(self._run_loop())
        logger.info("worker_started", interval_minutes=self._settings.dream_interval_minutes)
    
    async def stop(self):
        if self._task is None:
            return
        logger.info("worker_stopping")
        self._shutdown.set()
        try:
            await asyncio.wait_for(self._task, timeout=30.0)
        except asyncio.TimeoutError:
            logger.warning("worker_stop_timeout")
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        if self._own_llm_client:
            await self._llm_client.close()
        logger.info("worker_stopped")
    
    async def _run_loop(self):
        while not self._shutdown.is_set():
            try:
                await self._run_consolidation_cycle()
            except Exception as e:
                logger.exception("consolidation_cycle_failed", error=str(e))
                self._stats.record_error()
            
            try:
                await asyncio.wait_for(
                    self._shutdown.wait(),
                    timeout=self._settings.dream_interval_minutes * 60,
                )
                break
            except asyncio.TimeoutError:
                continue
    
    async def _run_consolidation_cycle(self):
        session_ids = self._get_active_sessions()
        if not session_ids:
            logger.debug("no_active_sessions_for_consolidation")
            return
        
        for session_id in session_ids:
            if self._shutdown.is_set():
                break
            result = await consolidate_session(
                session_id=session_id,
                llm_client=self._llm_client,
                prompt_loader=self._prompt_loader,
                episodic_repo=EpisodicRepository(self._db.get_session()),
                semantic_repo=MemoryRepository(self._db.get_session()),
                batch_size=self._settings.dream_batch_size,
                prompt_version=self._settings.consolidation_prompt_version,
                min_messages=self._settings.dream_min_messages,
            )
            self._stats.record_result(result, session_id)
    
    def _get_active_sessions(self) -> list[str]:
        with self._db.session() as session:
            repo = create_episodic_repository(session)
            return repo.get_session_ids(limit=self._settings.dream_batch_size)
    
    async def trigger_once(self, session_id: Optional[str] = None) -> ConsolidationResult:
        if session_id:
            return await consolidate_session(
                session_id=session_id,
                llm_client=self._llm_client,
                prompt_loader=self._prompt_loader,
                episodic_repo=EpisodicRepository(self._db.get_session()),
                semantic_repo=MemoryRepository(self._db.get_session()),
                batch_size=self._settings.dream_batch_size,
                prompt_version=self._settings.consolidation_prompt_version,
                min_messages=self._settings.dream_min_messages,
            )
        else:
            session_ids = self._get_active_sessions()
            if not session_ids:
                return ConsolidationResult(0, 0, 0, ["No active sessions"], 0)
            return await consolidate_session(
                session_id=session_ids[0],
                llm_client=self._llm_client,
                prompt_loader=self._prompt_loader,
                episodic_repo=EpisodicRepository(self._db.get_session()),
                semantic_repo=MemoryRepository(self._db.get_session()),
                batch_size=self._settings.dream_batch_size,
                prompt_version=self._settings.consolidation_prompt_version,
                min_messages=self._settings.dream_min_messages,
            )
    
    def get_stats(self) -> ConsolidationStats:
        return self._stats
    
    @property
    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()