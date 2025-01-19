"""empty message

Revision ID: 35cc6c8e6679
Revises: 0da05cbf693f
Create Date: 2025-01-04 01:53:10.340927

"""

import sqlalchemy as sa
import sqlmodel
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "35cc6c8e6679"
down_revision: str | None = "0da05cbf693f"
branch_labels: str | list[str] | None = None
depends_on: str | list[str] | None = None


def upgrade() -> None:
    """Upgrade to 'f39c64c35b39'"""
    op.add_column("mailings", sa.Column("country_code", sqlmodel.String(), nullable=True), schema="email")


def downgrade() -> None:
    """Downgrade to '0da05cbf693f'"""
    op.drop_column("mailings", "country_code", schema="email")
