import uuid
from datetime import datetime
from pydantic import BaseModel

class WorkoutPayload(BaseModel):
    id: uuid.UUID
    type: str  # "run" | "lift"
    started_at: datetime
    notes: str | None = None
    distance_m: int | None = None
    duration_s: int | None = None
    rpe: int | None = None
    version: int | None = None  # client known server version (0 for new)

class WorkoutSetPayload(BaseModel):
    id: uuid.UUID
    workout_id: uuid.UUID
    position: int = 0
    exercise_name: str | None = None
    reps: int | None = None
    weight_kg: float | None = None
    distance_m: int | None = None
    duration_s: int | None = None
    notes: str | None = None
    version: int | None = None
