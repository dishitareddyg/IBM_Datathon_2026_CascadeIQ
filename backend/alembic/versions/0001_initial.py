"""Initial optional persistence tables.

Revision ID: 0001
Revises:
Create Date: 2026-10-18
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "scenario_records",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("scenario_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("scenario_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "simulation_records",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("simulation_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("scenario_id", sa.String(length=64), nullable=False),
        sa.Column("result_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("simulation_records")
    op.drop_table("scenario_records")
