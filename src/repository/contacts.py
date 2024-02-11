from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.entity.models import Contact, User
from src.schemas.contact import ContactSchema, ContactUpdateSchema

from datetime import date
import datetime


async def get_contacts(limit: int, offset: int, db: AsyncSession, user: User):

    stmt = select(Contact).filter_by(user=user).offset(offset).limit(limit)
    contacts = await db.execute(stmt)
    return contacts.scalars().all()


async def get_all_contacts(limit: int, offset: int, db: AsyncSession, user: User):

    stmt = select(Contact).offset(offset).limit(limit)
    contacts = await db.execute(stmt)
    return contacts.scalars().all()


async def get_contact(contact_id: int, db: AsyncSession, user: User):

    stmt = select(Contact).filter_by(id=contact_id, user=user)
    contact = await db.execute(stmt)
    return contact.scalar_one_or_none()


async def get_contacts_by_birthday(today: date, end_date: date, db: AsyncSession, user: User):

    try:
        date_range_filter = and_(Contact.birthday >= today, Contact.birthday <= end_date)
        stmt = select(Contact).filter(date_range_filter)
        contacts = await db.execute(stmt)
        return contacts.scalars().all()
    except Exception as e:
        print(f"Error: {e}")
        return []


async def create_contact(body: ContactSchema, db: AsyncSession, user: User):

    contact = Contact(**body.model_dump(exclude_unset=True),
                      user=user)
    db.add(contact)
    await db.commit()
    await db.refresh(contact)
    return contact


async def update_contact(contact_id: int, body: ContactUpdateSchema, db: AsyncSession, user: User):

    stmt = select(Contact).filter_by(id=contact_id, user=user)
    result = await db.execute(stmt)
    contact = result.scalar_one_or_none()
    if contact:
        contact.first_name = body.first_name
        contact.last_name = body.last_name
        contact.email = body.email
        contact.phone = body.phone
        contact.birthday = body.birthday
        contact.additional_data = body.additional_data
        await db.commit()
        await db.refresh(contact)
    return contact


async def delete_contact(contact_id: int, db: AsyncSession, user: User):

    stmt = select(Contact).filter_by(id=contact_id, user=user)
    contact = await db.execute(stmt)
    contact = contact.scalar_one_or_none()
    if contact:
        await db.delete(contact)
        await db.commit()
    return contact