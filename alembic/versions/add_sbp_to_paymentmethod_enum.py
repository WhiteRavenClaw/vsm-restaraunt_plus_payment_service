"""add SBP to paymentmethod enum

Revision ID: add_sbp_paymentmethod
Revises: f2776f1024a9
Create Date: 2025-11-14 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_sbp_paymentmethod'
down_revision: Union[str, Sequence[str], None] = 'f2776f1024a9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Добавляем SBP в enum paymentmethod
    # В PostgreSQL нужно использовать ALTER TYPE ... ADD VALUE
    op.execute("ALTER TYPE paymentmethod ADD VALUE IF NOT EXISTS 'SBP'")


def downgrade() -> None:
    """Downgrade schema."""
    # В PostgreSQL нельзя удалить значение из enum напрямую
    # Нужно пересоздать enum, но это сложно, поэтому оставляем пустым
    # или можно пересоздать enum без SBP
    pass

