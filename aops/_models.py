import uuid
from datetime import datetime

from pydantic import BaseModel


class AgentModel(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime


class ChainModel(BaseModel):
    id: uuid.UUID
    agent_id: uuid.UUID
    name: str
    description: str | None
    persona: str | None
    content: str
    created_at: datetime
    updated_at: datetime


class ChainVersionModel(BaseModel):
    id: uuid.UUID
    chain_id: uuid.UUID
    persona: str | None
    content: str
    message: str
    version_number: int
    created_at: datetime
