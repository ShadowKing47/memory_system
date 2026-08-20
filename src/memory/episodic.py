from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy import Index, select
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Session

from .models import Base, EpisodicLog


class EpisodicRepository:
    def __init__(self, session: Session):
        self._session = session
    
    def add_log(
        self,
        session_id: str,
        role: str,
        content: str,
        meta: dict | None = None,
    ) -> EpisodicLog:
        log = EpisodicLog(
            session_id=session_id,
            role=role,
            content=content,
            meta=meta or {},
        )
        self._session.add(log)
        self._session.flush()
        return log
    
    def get_recent(self, session_id: str, limit: int = 50) -> list[EpisodicLog]:
        stmt = (
            select(EpisodicLog)
            .where(EpisodicLog.session_id == session_id)
            .order_by(EpisodicLog.created_at.desc())
            .limit(limit)
        )
        return list(self._session.execute(stmt).scalars().all())
    
    def get_all_recent(self, limit: int = 100) -> list[EpisodicLog]:
        stmt = select(EpisodicLog).order_by(EpisodicLog.created_at.desc()).limit(limit)
        return list(self._session.execute(stmt).scalars().all())
    
    def get_session_ids(self, limit: int = 50) -> list[str]:
        stmt = (
            select(EpisodicLog.session_id)
            .distinct()
            .order_by(EpisodicLog.created_at.desc())
            .limit(limit)
        )
        return list(self._session.execute(stmt).scalars().all())
    
    def count_by_session(self, session_id: str) -> int:
        stmt = select(EpisodicLog).where(EpisodicLog.session_id == session_id)
        return len(list(self._session.execute(stmt).scalars().all()))
    
    def delete_old_logs(self, days: int = 30) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        stmt = select(EpisodicLog).where(EpisodicLog.created_at < cutoff)
        logs = list(self._session.execute(stmt).scalars().all())
        for log in logs:
            self._session.delete(log)
        return len(logs)


def create_episodic_repository(session: Session) -> EpisodicRepository:
    return EpisodicRepository(session)