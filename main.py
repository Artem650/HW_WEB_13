import os
import re
from typing import Callable
from fastapi import FastAPI, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import text, select
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from ipaddress import ip_address

import uvicorn

from src.database.db import get_db
from src.routes import contacts, users
from src.routes import auth
from src.entity.models import Contact
from src.repository import contacts as reps_contacts

import redis.asyncio as redis
from fastapi_limiter import FastAPILimiter

from src.conf.config import config


app = FastAPI()
banned_ips = [
    ip_address("192.168.1.1"),
    ip_address("192.168.1.2"),
]

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def ban_ips(request: Request, call_next: Callable):
    ip = ip_address(request.client.host)
    if ip in banned_ips:
        return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content={"detail": "You are banned"})
    response = await call_next(request)
    return response


app.include_router(auth.router, prefix="/api")
app.include_router(contacts.router, prefix="/api")
app.include_router(users.router, prefix="/api")

@app.on_event("startup")
async def startup():
    r = await redis.Redis(
        host=config.REDIS_DOMAIN,
        port=config.REDIS_PORT,
        db=0,
        password=config.REDIS_PASSWORD,
    )
    await FastAPILimiter.init(r)

@app.get("/")
def index():
    return {"message": "Contact Application"}

@app.get("/api/healthchecker")
async def healthchecker(db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(text("SELECT 1"))
        result = result.fetchone()
        if result is None:
            raise HTTPException(status_code=500, detail="Database is not configured correctly")
        return {"message": "Welcome to FastAPI!"}
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Error connecting to the database")


@app.get("/find_contact")
async def find_contact(
    db: AsyncSession = Depends(get_db),
    first_name: str = Query(None, min_length=3, max_length=50),
    last_name: str = Query(None, min_length=3, max_length=50),
    email: str = Query(None, regex=r'^[\w\.-]+@[\w\.-]+\.\w+$')
):
    filters = []
    if first_name:
        filters.append(Contact.first_name == first_name)
    if last_name:
        filters.append(Contact.last_name == last_name)
    if email:
        filters.append(Contact.email == email)

    query = select(Contact).filter(*filters)
    result = await db.execute(query)
    contacts = result.scalars().all()

    return {"contacts": contacts}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), log_level="info")