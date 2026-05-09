"""received_at as datetime

Revision ID: 3eaaa225e53d
Revises: 265b4db26c22
Create Date: 2026-05-08 17:35:21.756359

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3eaaa225e53d'
down_revision: Union[str, Sequence[str], None] = '265b4db26c22'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1 — clear unparseable existing text values
    op.execute("UPDATE emails SET received_at = NULL")

    # Step 2 — now safe to cast since all values are NULL
    op.alter_column('emails', 'received_at',
               existing_type=sa.TEXT(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=True,
               postgresql_using="received_at::timestamp with time zone")


def downgrade() -> None:
    op.alter_column('emails', 'received_at',
               existing_type=sa.DateTime(timezone=True),
               type_=sa.TEXT(),
               existing_nullable=True,
               postgresql_using="received_at::text")
    # ### end Alembic commands ###
