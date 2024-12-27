"""initial revision

Revision ID: 0a992057b082
Revises:
Create Date: 2024-12-26 11:55:27.449701

"""

import sqlalchemy as sa
import sqlmodel
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "0a992057b082"
down_revision: str | None = None
branch_labels: str | list[str] | None = None
depends_on: str | list[str] | None = None


def upgrade() -> None:
    """Upgrade to '0a992057b082'"""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "downloads",
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sqlmodel.String(), nullable=False),
        sa.Column("name", sqlmodel.String(), nullable=False),
        sa.Column("link", sqlmodel.String(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_downloaded", sa.Boolean(), nullable=False),
        sa.Column("downloaded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("presigned_url", sqlmodel.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema="download",
    )
    op.create_index(op.f("ix_download_downloads_created_at"), "downloads", ["created_at"], unique=False, schema="download")
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade to None"""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f("ix_download_downloads_created_at"), table_name="downloads", schema="download")
    op.drop_table("downloads", schema="download")
    # ### end Alembic commands ###
