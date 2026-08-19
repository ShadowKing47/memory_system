from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class SemanticMemoryBase(BaseModel):
    entity: str = Field(..., min_length=1, max_length=255)
    fact: str = Field(..., min_length=1)
    source: Optional[str] = Field(None, max_length=255)


class SemanticMemoryCreate(SemanticMemoryBase):
    pass


class SemanticMemoryUpdate(BaseModel):
    fact: str = Field(..., min_length=1)
    source: Optional[str] = Field(None, max_length=255)


class SemanticMemoryRead(SemanticMemoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    valid_from: datetime
    valid_to: Optional[datetime] = None


class SemanticMemorySearchResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    entity: str
    fact: str
    source: Optional[str] = None
    valid_from: datetime
    valid_to: Optional[datetime] = None