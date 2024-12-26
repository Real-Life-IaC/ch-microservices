from pydantic import BaseModel
from pydantic.networks import EmailStr


class Email(BaseModel):
    """Pydantic model to process email data"""

    name: str
    email: EmailStr
    presigned_url: str
    link: str
    message_id: str | None = None
