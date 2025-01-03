from uuid import UUID

from pydantic import BaseModel, EmailStr


class BookRequest(BaseModel):
    """Pydantic model to process the book request email"""

    id: UUID
    name: str
    email: EmailStr
    presigned_url: str
    link: str
    message_id: str | None = None
