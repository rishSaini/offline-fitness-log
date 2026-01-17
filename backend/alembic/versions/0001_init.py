"""init

Revision ID: 0001_init
Revises:
Create Date: 2026-01-17
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    workout_type = postgresql.ENUM("run", "lift", name="workout_type")
    workout_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "workouts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("type", postgresql.ENUM("run", "lift", name="workout_type", create_type=False), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("distance_m", sa.Integer(), nullable=True),
        sa.Column("duration_s", sa.Integer(), nullable=True),
        sa.Column("rpe", sa.Integer(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_workouts_user_id", "workouts", ["user_id"], unique=False)

    op.create_table(
        "workout_sets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("workout_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workouts.id"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("exercise_name", sa.String(length=200), nullable=True),
        sa.Column("reps", sa.Integer(), nullable=True),
        sa.Column("weight_kg", sa.Numeric(8, 2), nullable=True),
        sa.Column("distance_m", sa.Integer(), nullable=True),
        sa.Column("duration_s", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_workout_sets_user_id", "workout_sets", ["user_id"], unique=False)
    op.create_index("ix_workout_sets_workout_id", "workout_sets", ["workout_id"], unique=False)

    op.create_table(
        "sync_ops",
        sa.Column("op_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_sync_ops_user_id", "sync_ops", ["user_id"], unique=False)


def downgrade():
    op.drop_index("ix_sync_ops_user_id", table_name="sync_ops")
    op.drop_table("sync_ops")

    op.drop_index("ix_workout_sets_workout_id", table_name="workout_sets")
    op.drop_index("ix_workout_sets_user_id", table_name="workout_sets")
    op.drop_table("workout_sets")

    op.drop_index("ix_workouts_user_id", table_name="workouts")
    op.drop_table("workouts")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

    workout_type = postgresql.ENUM("run", "lift", name="workout_type")
    workout_type.drop(op.get_bind(), checkfirst=True)
