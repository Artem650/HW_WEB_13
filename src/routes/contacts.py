from fastapi import APIRouter, HTTPException, Depends, status, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession
from src.entity.models import User
from src.services.auth import auth_service
from src.database.db import get_db
from src.repository import contacts as reps_contacts
from src.schemas.contact import ContactSchema, ContactUpdateSchema, ContactResponse

import re
from datetime import date, timedelta

router = APIRouter(prefix='/contacts', tags=['contacts'])


@router.get("/", response_model=list[ContactResponse])
async def get_contacts(limit: int = Query(10, ge=10, le=500), offset: int = Query(0, ge=0),
                       db: AsyncSession = Depends(get_db),
                       user: User = Depends(auth_service.get_current_user)
                       ):
    contacts = await reps_contacts.get_contacts(limit, offset, db, user)
    return contacts


@router.get("/all", response_model=list[ContactResponse])
async def get_contacts(limit: int = Query(10, ge=10, le=500), offset: int = Query(0, ge=0),
                       db: AsyncSession = Depends(get_db),
                       user: User = Depends(auth_service.get_current_user)
                       ):
    contacts = await reps_contacts.get_all_contacts(limit, offset, db, user)
    return contacts


@router.get("/{contact_id}", response_model=ContactResponse)
async def get_contact(contact_id: int = Path(ge=1), db: AsyncSession = Depends(get_db),
                      user: User = Depends(auth_service.get_current_user)
                      ):
    contact = await reps_contacts.get_contact(contact_id, db, user)
    if contact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="NOT FOUND")
    return contact


@router.get("/birthdays/", response_model=list[ContactResponse])
async def get_contact_by_bday(
        days_ahead: int = Query(7, description="Number of days ahead to search for birthdays"),
        db: AsyncSession = Depends(get_db),
        user: User = Depends(auth_service.get_current_user)
):
    today = date.today()
    end_date = today + timedelta(days=days_ahead)
    contacts = await reps_contacts.get_contacts_by_birthday(today, end_date, db, user)
    if contacts is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="NOT FOUND")
    return contacts


@router.post("/", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
async def create_contact(body: ContactSchema, db: AsyncSession = Depends(get_db),
                         user: User = Depends(auth_service.get_current_user)
                         ):

    if not re.match(r'^[\d\+\(\)]+$', body.phone):
        raise HTTPException(status_code=422, detail="Input valid phone")
    contact = await reps_contacts.create_contact(body, db, user)
    return contact


@router.put("/{contact_id}")
async def update_contact(body: ContactUpdateSchema, contact_id: int = Path(ge=1), db: AsyncSession = Depends(get_db),
                         user: User = Depends(auth_service.get_current_user)
                         ):

    contact = await reps_contacts.update_contact(contact_id, body, db, user)
    if contact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="NOT FOUND")
    return contact


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contact(contact_id: int = Path(ge=1), db: AsyncSession = Depends(get_db),
                         user: User = Depends(auth_service.get_current_user)
                         ):

    contact = await reps_contacts.delete_contact(contact_id, db, user)
    return contact