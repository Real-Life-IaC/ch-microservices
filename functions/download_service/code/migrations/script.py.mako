"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
import sqlalchemy as sa
import sqlmodel
from alembic import op

${imports if imports else ""}

# revision identifiers, used by Alembic.
revision: str = ${repr(up_revision)}
down_revision: str | None = ${repr(down_revision)}
branch_labels: str | list[str] | None = ${repr(branch_labels)}
depends_on: str | list[str] | None = ${repr(depends_on)}


def upgrade() -> None:
    """Upgrade to ${repr(up_revision)}"""
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    """Downgrade to ${repr(down_revision)}"""
    ${downgrades if downgrades else "pass"}
