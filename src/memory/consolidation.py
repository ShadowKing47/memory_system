import json
import time
from dataclasses import dataclass
from typing import Optional

from .llm.protocol import LLMClientProtocol, LLMResponse
from .prompts.loader import PromptLoader
from .episodic import EpisodicLog, EpisodicRepository
from .repository import MemoryRepository
from .schemas import SemanticMemoryCreate, SemanticMemoryUpdate
from .logging import get_logger


logger = get_logger(__name__)


@dataclass(frozen=True)
class ConsolidatedFact:
    entity: str
    fact: str
    is_update: bool


@dataclass(frozen=True)
class ConsolidationResult:
    facts_extracted: int
    facts_upserted: int
    facts_superseded: int
    errors: list[str]
    duration_ms: int


def format_logs_for_prompt(logs: list[EpisodicLog]) -> str:
    if not logs:
        return "(empty)"
    
    formatted = []
    for log in reversed(logs):  # Chronological order
        role = log.role.upper()
        content = log.content.strip()
        meta = log.meta
        if meta:
            meta_str = f" [meta: {json.dumps(meta)}]"
        else:
            meta_str = ""
        formatted.append(f"{role}: {content}{meta_str}")
    
    return "\n".join(formatted)


def parse_consolidation_response(content: str) -> list[ConsolidatedFact]:
    try:
        data = json.loads(content.strip())
    except json.JSONDecodeError as e:
        logger.warning("consolidation_json_parse_failed", error=str(e), content=content[:200])
        raise ValueError(f"Invalid JSON response: {e}")
    
    if not isinstance(data, list):
        raise ValueError("Response must be a JSON array")
    
    facts = []
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            logger.warning("consolidation_item_not_dict", index=i, item=item)
            continue
        
        entity = item.get("entity")
        fact = item.get("fact")
        is_update = item.get("is_update", False)
        
        if not entity or not fact:
            logger.warning("consolidation_missing_fields", index=i, item=item)
            continue
        
        if not isinstance(entity, str) or not isinstance(fact, str):
            logger.warning("consolidation_invalid_types", index=i, item=item)
            continue
        
        facts.append(ConsolidatedFact(
            entity=entity.strip(),
            fact=fact.strip(),
            is_update=bool(is_update),
        ))
    
    return facts


def validate_facts(facts: list[ConsolidatedFact]) -> list[ConsolidatedFact]:
    seen = set()
    validated = []
    for fact in facts:
        key = (fact.entity.lower(), fact.fact.lower())
        if key in seen:
            logger.warning("consolidation_duplicate_fact", entity=fact.entity, fact=fact.fact)
            continue
        seen.add(key)
        validated.append(fact)
    return validated


async def upsert_facts(
    facts: list[ConsolidatedFact],
    semantic_repo: MemoryRepository,
) -> tuple[int, int]:
    upserted = 0
    superseded = 0
    
    for fact in facts:
        try:
            if fact.is_update:
                semantic_repo.supersede_fact(
                    fact.entity,
                    SemanticMemoryUpdate(fact=fact.fact, source="consolidation"),
                )
                superseded += 1
            else:
                semantic_repo.add_fact(
                    SemanticMemoryCreate(entity=fact.entity, fact=fact.fact, source="consolidation"),
                )
                upserted += 1
        except Exception as e:
            logger.exception("consolidation_upsert_failed", entity=fact.entity, error=str(e))
            raise
    
    return upserted, superseded


async def consolidate_session(
    session_id: str,
    llm_client: LLMClientProtocol,
    prompt_loader: PromptLoader,
    episodic_repo: EpisodicRepository,
    semantic_repo: MemoryRepository,
    batch_size: int = 50,
    prompt_version: str = "latest",
    min_messages: int = 10,
) -> ConsolidationResult:
    start_time = time.perf_counter()
    errors = []
    
    try:
        logs = episodic_repo.get_recent(session_id, limit=batch_size)
        
        if len(logs) < min_messages:
            return ConsolidationResult(
                facts_extracted=0,
                facts_upserted=0,
                facts_superseded=0,
                errors=[f"Insufficient messages: {len(logs)} < {min_messages}"],
                duration_ms=int((time.perf_counter() - start_time) * 1000),
            )
        
        prompt = prompt_loader.load("consolidation", prompt_version)
        chat_logs = format_logs_for_prompt(logs)
        full_prompt = prompt.replace("{{chat_logs}}", chat_logs)
        
        messages = [{"role": "user", "content": full_prompt}]
        response = await llm_client.complete(
            messages=messages,
            model="nvidia/nemotron-3-ultra-550b-a55b:free",
            max_tokens=1024,
            temperature=0.1,
            enable_reasoning=True,
        )
        
        facts = parse_consolidation_response(response.content)
        validated = validate_facts(facts)
        
        if validated:
            upserted, superseded = await upsert_facts(validated, semantic_repo)
        else:
            upserted = superseded = 0
        
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        logger.info(
            "consolidation_completed",
            session_id=session_id,
            facts_extracted=len(validated),
            upserted=upserted,
            superseded=superseded,
            duration_ms=duration_ms,
        )
        
        return ConsolidationResult(
            facts_extracted=len(validated),
            facts_upserted=upserted,
            facts_superseded=superseded,
            errors=errors,
            duration_ms=duration_ms,
        )
    
    except Exception as e:
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        error_msg = f"Consolidation failed: {e}"
        logger.exception("consolidation_failed", session_id=session_id, error=str(e))
        errors.append(error_msg)
        
        return ConsolidationResult(
            facts_extracted=0,
            facts_upserted=0,
            facts_superseded=0,
            errors=errors,
            duration_ms=duration_ms,
        )