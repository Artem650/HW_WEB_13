from typing import Optional

from pydantic import BaseModel, EmailStr, Field, ConfigDict
from datetime import date, datetime
from sqlalchemy import CheckConstraint
from src.schemas.user import UserResponse


class ContactSchema(BaseModel):
    first_name: str = Field(min_length=3, max_length=50)
    last_name: str = Field(min_length=3, max_length=50)
    email: str = EmailStr
    phone: str = Field(min_length=3, max_length=25)
    birthday: date
    additional_data: str = None


class ContactUpdateSchema(ContactSchema):
    completed: bool


class ContactResponse(BaseModel):
    id: int = 1
    first_name: str
    last_name: str
    email: str
    phone: str
    birthday: date
    additional_data: str = None
    created_at: datetime | None
    updated_at: datetime | None
    user: UserResponse | None

    class Config:
        from_attributes = True