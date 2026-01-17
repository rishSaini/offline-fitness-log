import uuid
from typing import Any, Literal
from pydantic import BaseModel

OpType = Literal["UPSERT_WORKOUT", "DELETE_WORKOUT", "UPSERT_SET", "DELETE_SET"]


class SyncOpIn(BaseModel):
    op_id: uuid.UUID
    type: OpType
    entity_id: uuid.UUID
    payload: dict[str, Any] | None = None
    client_updated_at: int  # ms since epoch


class SyncPushRequest(BaseModel):
    ops: list[SyncOpIn]


class EntityOut(BaseModel):
    kind: Literal["workout", "workout_set"]
    data: dict[str, Any]


class ConflictOut(BaseModel):
    op_id: uuid.UUID
    type: OpType
    entity: EntityOut


class SyncPushResponse(BaseModel):
    applied_op_ids: list[uuid.UUID]
    updated_entities: list[EntityOut]
    conflicts: list[ConflictOut]
    server_time_ms: int
