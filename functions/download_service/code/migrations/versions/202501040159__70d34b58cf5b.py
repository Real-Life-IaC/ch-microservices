"""empty message

Revision ID: 70d34b58cf5b
Revises: 83367e99b9c5
Create Date: 2025-01-04 01:59:46.543414

"""

import sqlalchemy as sa
import sqlmodel
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "70d34b58cf5b"
down_revision: str | None = "83367e99b9c5"
branch_labels: str | list[str] | None = None
depends_on: str | list[str] | None = None


def upgrade() -> None:
    """Upgrade to 'f39c64c35b39'"""
    op.add_column("downloads", sa.Column("country_code", sqlmodel.String(), nullable=True), schema="download")


def downgrade() -> None:
    """Downgrade to '0da05cbf693f'"""
    op.drop_column("downloads", "country_code", schema="download")
