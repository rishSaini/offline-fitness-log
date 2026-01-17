from __future__ import annotations

import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.sync_op import SyncOp
from app.models.workout import Workout, WorkoutSet
from app.schemas.sync import SyncPushRequest, SyncPushResponse, EntityOut, ConflictOut


router = APIRouter(prefix="/sync", tags=["sync"])


def _dt_iso(dt: datetime | None) -> str | None:
    return dt.astimezone(timezone.utc).isoformat() if dt else None


def _serialize_workout(w: Workout) -> dict:
    return {
        "id": str(w.id),
        "user_id": str(w.user_id),
        "type": w.type,
        "started_at": _dt_iso(w.started_at),
        "notes": w.notes,
        "distance_m": w.distance_m,
        "duration_s": w.duration_s,
        "rpe": w.rpe,
        "version": w.version,
        "updated_at": _dt_iso(w.updated_at),
        "deleted_at": _dt_iso(w.deleted_at),
    }


def _serialize_set(s: WorkoutSet) -> dict:
    return {
        "id": str(s.id),
        "user_id": str(s.user_id),
        "workout_id": str(s.workout_id),
        "position": s.position,
        "exercise_name": s.exercise_name,
        "reps": s.reps,
        "weight_kg": float(s.weight_kg) if s.weight_kg is not None else None,
        "distance_m": s.distance_m,
        "duration_s": s.duration_s,
        "notes": s.notes,
        "version": s.version,
        "updated_at": _dt_iso(s.updated_at),
        "deleted_at": _dt_iso(s.deleted_at),
    }


@router.post("/push", response_model=SyncPushResponse)
def sync_push(
    req: SyncPushRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    applied_op_ids: list = []
    updated_entities: list[EntityOut] = []
    conflicts: list[ConflictOut] = []

    now = datetime.now(timezone.utc)

    for op in req.ops:
        # Idempotency: if already applied, skip
        if db.get(SyncOp, op.op_id):
            applied_op_ids.append(op.op_id)
            continue

        if op.type == "UPSERT_WORKOUT":
            payload = op.payload or {}
            client_version = int(payload.get("version") or 0)

            existing: Workout | None = (
                db.query(Workout)
                .filter(Workout.id == op.entity_id, Workout.user_id == user.id)
                .one_or_none()
            )

            if existing and client_version < existing.version:
                conflicts.append(
                    ConflictOut(
                        op_id=op.op_id,
                        type=op.type,
                        entity=EntityOut(kind="workout", data=_serialize_workout(existing)),
                    )
                )
                continue

            if not existing:
                w = Workout(
                    id=op.entity_id,
                    user_id=user.id,
                    type=str(payload["type"]),
                    started_at=datetime.fromisoformat(payload["started_at"]),
                    notes=payload.get("notes"),
                    distance_m=payload.get("distance_m"),
                    duration_s=payload.get("duration_s"),
                    rpe=payload.get("rpe"),
                    version=1,
                    updated_at=now,
                    deleted_at=None,
                )
                db.add(w)
                db.flush()
                updated_entities.append(EntityOut(kind="workout", data=_serialize_workout(w)))
            else:
                existing.type = str(payload.get("type", existing.type))
                if payload.get("started_at"):
                    existing.started_at = datetime.fromisoformat(payload["started_at"])
                existing.notes = payload.get("notes", existing.notes)
                existing.distance_m = payload.get("distance_m", existing.distance_m)
                existing.duration_s = payload.get("duration_s", existing.duration_s)
                existing.rpe = payload.get("rpe", existing.rpe)
                existing.version = existing.version + 1
                existing.updated_at = now
                updated_entities.append(EntityOut(kind="workout", data=_serialize_workout(existing)))

            db.add(SyncOp(op_id=op.op_id, user_id=user.id))
            applied_op_ids.append(op.op_id)

        elif op.type == "DELETE_WORKOUT":
            existing: Workout | None = (
                db.query(Workout)
                .filter(Workout.id == op.entity_id, Workout.user_id == user.id)
                .one_or_none()
            )
            if existing and existing.deleted_at is None:
                existing.deleted_at = now
                existing.version += 1
                existing.updated_at = now
                updated_entities.append(EntityOut(kind="workout", data=_serialize_workout(existing)))

            db.add(SyncOp(op_id=op.op_id, user_id=user.id))
            applied_op_ids.append(op.op_id)

        elif op.type == "UPSERT_SET":
            payload = op.payload or {}
            client_version = int(payload.get("version") or 0)

            existing: WorkoutSet | None = (
                db.query(WorkoutSet)
                .filter(WorkoutSet.id == op.entity_id, WorkoutSet.user_id == user.id)
                .one_or_none()
            )

            if existing and client_version < existing.version:
                conflicts.append(
                    ConflictOut(
                        op_id=op.op_id,
                        type=op.type,
                        entity=EntityOut(kind="workout_set", data=_serialize_set(existing)),
                    )
                )
                continue

            if not existing:
                s = WorkoutSet(
                    id=op.entity_id,
                    user_id=user.id,
                    workout_id=payload["workout_id"],
                    position=int(payload.get("position") or 0),
                    exercise_name=payload.get("exercise_name"),
                    reps=payload.get("reps"),
                    weight_kg=payload.get("weight_kg"),
                    distance_m=payload.get("distance_m"),
                    duration_s=payload.get("duration_s"),
                    notes=payload.get("notes"),
                    version=1,
                    updated_at=now,
                    deleted_at=None,
                )
                db.add(s)
                db.flush()
                updated_entities.append(EntityOut(kind="workout_set", data=_serialize_set(s)))
            else:
                if payload.get("workout_id"):
                    existing.workout_id = payload["workout_id"]
                existing.position = int(payload.get("position", existing.position))
                existing.exercise_name = payload.get("exercise_name", existing.exercise_name)
                existing.reps = payload.get("reps", existing.reps)
                existing.weight_kg = payload.get("weight_kg", existing.weight_kg)
                existing.distance_m = payload.get("distance_m", existing.distance_m)
                existing.duration_s = payload.get("duration_s", existing.duration_s)
                existing.notes = payload.get("notes", existing.notes)
                existing.version += 1
                existing.updated_at = now
                updated_entities.append(EntityOut(kind="workout_set", data=_serialize_set(existing)))

            db.add(SyncOp(op_id=op.op_id, user_id=user.id))
            applied_op_ids.append(op.op_id)

        elif op.type == "DELETE_SET":
            existing: WorkoutSet | None = (
                db.query(WorkoutSet)
                .filter(WorkoutSet.id == op.entity_id, WorkoutSet.user_id == user.id)
                .one_or_none()
            )
            if existing and existing.deleted_at is None:
                existing.deleted_at = now
                existing.version += 1
                existing.updated_at = now
                updated_entities.append(EntityOut(kind="workout_set", data=_serialize_set(existing)))

            db.add(SyncOp(op_id=op.op_id, user_id=user.id))
            applied_op_ids.append(op.op_id)

    db.commit()

    return SyncPushResponse(
        applied_op_ids=applied_op_ids,
        updated_entities=updated_entities,
        conflicts=conflicts,
        server_time_ms=int(time.time() * 1000),
    )
