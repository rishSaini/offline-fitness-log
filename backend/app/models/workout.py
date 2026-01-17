import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Numeric, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

WorkoutType = Enum("run", "lift", name="workout_type")


class Workout(Base):
    __tablename__ = "workouts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)  # client-generated
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False)

    type: Mapped[str] = mapped_column(WorkoutType, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Optional run metrics (MVP)
    distance_m: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_s: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rpe: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Sync fields
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    sets: Mapped[list["WorkoutSet"]] = relationship("WorkoutSet", back_populates="workout")


class WorkoutSet(Base):
    __tablename__ = "workout_sets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)  # client-generated
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False)
    workout_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workouts.id"), index=True, nullable=False)

    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Lifting fields (optional)
    exercise_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    reps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)

    # Running interval fields (optional)
    distance_m: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_s: Mapped[int | None] = mapped_column(Integer, nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Sync fields
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    workout: Mapped["Workout"] = relationship("Workout", back_populates="sets")
