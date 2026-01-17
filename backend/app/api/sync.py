from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import APIRouter, Header, HTTPException
from jose import JWTError, jwt
from pydantic import BaseModel

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

router = APIRouter(prefix="/sync", tags=["sync"])

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://fitness:fitness@localhost:5432/fitness",
)

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_ALG = "HS256"

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class SyncOp(BaseModel):
    op_id: uuid.UUID
    type: Literal["UPSERT_WORKOUT", "DELETE_WORKOUT"]
    entity_id: uuid.UUID
    payload: dict[str, Any] | None = None
    client_updated_at: int


class SyncPushRequest(BaseModel):
    ops: list[SyncOp]


class SyncResponse(BaseModel):
    applied_op_ids: list[str]
    updated_entities: list[dict[str, Any]]
    conflicts: list[dict[str, Any]]
    server_time_ms: int


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _get_user_id_from_auth(authorization: str | None) -> uuid.UUID:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing/invalid Authorization header")

    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        sub = payload.get("sub")
        if not sub:
            raise HTTPException(status_code=401, detail="Token missing subject")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    # sub might be uuid (recommended) or email
    user_id: uuid.UUID | None = None
    try:
        user_id = uuid.UUID(str(sub))
    except Exception:
        user_id = None

    with SessionLocal() as db:
        if user_id is not None:
            row = db.execute(
                text("SELECT id FROM users WHERE id = :id"),
                {"id": str(user_id)},
            ).fetchone()
            if row:
                return uuid.UUID(str(row[0]))

        # treat as email
        row = db.execute(
            text("SELECT id FROM users WHERE email = :email"),
            {"email": str(sub)},
        ).fetchone()
        if not row:
            raise HTTPException(status_code=401, detail="User not found")
        return uuid.UUID(str(row[0]))


@router.post("/push", response_model=SyncResponse)
def push(req: SyncPushRequest, authorization: str | None = Header(default=None)):
    user_id = _get_user_id_from_auth(authorization)
    applied: list[str] = []
    updated_entities: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    now = _now()

    with SessionLocal() as db:
        for op in req.ops:
            if op.type == "UPSERT_WORKOUT":
                if not op.payload:
                    # nothing to apply; mark as done
                    applied.append(str(op.op_id))
                    continue

                w = op.payload
                workout_id = str(w.get("id") or op.entity_id)
                wtype = w.get("type")
                started_at = w.get("started_at")
                notes = w.get("notes")
                distance_m = w.get("distance_m")
                duration_s = w.get("duration_s")
                rpe = w.get("rpe")
                client_version = int(w.get("version") or 0)

                # Fetch server version
                row = db.execute(
                    text("""
                        SELECT id, type, started_at, notes, distance_m, duration_s, rpe,
                               version, updated_at, deleted_at
                        FROM workouts
                        WHERE id = :id AND user_id = :user_id
                    """),
                    {"id": workout_id, "user_id": str(user_id)},
                ).fetchone()

                if row is None:
                    # Insert as version 1
                    db.execute(
                    text("""
                        INSERT INTO workouts
                        (id, user_id, type, started_at, notes, distance_m, duration_s, rpe, version, updated_at, deleted_at)
                        VALUES
                        (:id, :user_id, :type, CAST(:started_at AS timestamptz), :notes, :distance_m, :duration_s, :rpe, 1, CAST(:updated_at AS timestamptz), NULL)
                        """),
                        {
                            "id": workout_id,
                            "user_id": str(user_id),
                            "type": wtype,
                            "started_at": started_at,
                            "notes": notes,
                            "distance_m": distance_m,
                            "duration_s": duration_s,
                            "rpe": rpe,
                            "updated_at": now.isoformat(),
                        },
                    )
                    server_version = 1
                else:
                    server_version = int(row[7] or 0)

                    # conflict: server ahead
                    if client_version < server_version:
                        conflicts.append(
                            {
                                "op_id": str(op.op_id),
                                "entity": "workout",
                                "entity_id": workout_id,
                                "reason": "client_version_behind",
                                "server": {
                                    "id": str(row[0]),
                                    "type": row[1],
                                    "started_at": row[2].isoformat() if row[2] else None,
                                    "notes": row[3],
                                    "distance_m": row[4],
                                    "duration_s": row[5],
                                    "rpe": row[6],
                                    "version": server_version,
                                    "updated_at": row[8].isoformat() if row[8] else None,
                                    "deleted_at": row[9].isoformat() if row[9] else None,
                                },
                            }
                        )
                        # For MVP: server wins, mark op as applied and also return server state as “updated entity”
                        applied.append(str(op.op_id))
                        updated_entities.append({"entity": "workout", "data": conflicts[-1]["server"]})
                        continue

                    # apply update
                    new_version = server_version + 1
                    db.execute(
                    text("""
                        UPDATE workouts SET
                        type = :type,
                        started_at = CAST(:started_at AS timestamptz),
                        notes = :notes,
                        distance_m = :distance_m,
                        duration_s = :duration_s,
                        rpe = :rpe,
                        version = :version,
                        updated_at = CAST(:updated_at AS timestamptz),
                        deleted_at = NULL
                        WHERE id = :id AND user_id = :user_id
                    """),
                    {
                        "id": workout_id,
                        "user_id": str(user_id),
                        "type": wtype,
                        "started_at": started_at,
                        "notes": notes,
                        "distance_m": distance_m,
                        "duration_s": duration_s,
                        "rpe": rpe,
                        "version": new_version,
                        "updated_at": now.isoformat(),
                    },
                )

                    server_version = new_version

                # return server copy so mobile can update local version
                updated_entities.append(
                    {
                        "entity": "workout",
                        "data": {
                            "id": workout_id,
                            "type": wtype,
                            "started_at": started_at,
                            "notes": notes,
                            "distance_m": distance_m,
                            "duration_s": duration_s,
                            "rpe": rpe,
                            "version": server_version,
                            "updated_at": now.isoformat(),
                            "deleted_at": None,
                        },
                    }
                )
                applied.append(str(op.op_id))

            elif op.type == "DELETE_WORKOUT":
                workout_id = str(op.entity_id)
                # soft delete
                row = db.execute(
                    text("SELECT version FROM workouts WHERE id=:id AND user_id=:user_id"),
                    {"id": workout_id, "user_id": str(user_id)},
                ).fetchone()
                if row:
                    new_version = int(row[0] or 0) + 1
                    db.execute(
                        text("""
                            UPDATE workouts SET
                            deleted_at = CAST(:deleted_at AS timestamptz),
                            updated_at = CAST(:updated_at AS timestamptz),
                            version = :version
                            WHERE id = :id AND user_id = :user_id
                        """),
                    {
                        "id": workout_id,
                        "user_id": str(user_id),
                        "deleted_at": now.isoformat(),
                        "updated_at": now.isoformat(),
                        "version": new_version,
                    },
                )

                applied.append(str(op.op_id))

        db.commit()

    return SyncResponse(
        applied_op_ids=applied,
        updated_entities=updated_entities,
        conflicts=conflicts,
        server_time_ms=int(now.timestamp() * 1000),
    )
