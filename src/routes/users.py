import pickle

import cloudinary
import cloudinary.uploader

from fastapi import APIRouter, File, HTTPException, Request, Depends, UploadFile, status, Path, Query, Security, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from src.entity.models import User
from src.schemas.user import UserResponse
from src.services.auth import auth_service
from src.repository import users as reps_users
from fastapi_limiter.depends import RateLimiter
from src.conf.config import config
from src.database.db import get_db

router = APIRouter(prefix="/users", tags=["users"])


cloudinary.config(
    cloud_name=config.CLD_NAME,
    api_key=config.CLD_API_KEY,
    api_secret=config.CLD_API_SECRET,
    secure=True,
)


@router.get("/me", response_model=UserResponse, dependencies=[Depends(RateLimiter(times=1, seconds=20))])
async def get_current_user(user: User = Depends(auth_service.get_current_user)):

    return user


@router.patch(
    "/avatar",
    response_model=UserResponse,
    dependencies=[Depends(RateLimiter(times=1, seconds=20))],
)
async def get_current_user(
    file: UploadFile = File(),
    user: User = Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db),
):


    public_id = f"Web17/{user.email}"
    res = cloudinary.uploader.upload(file.file, public_id=public_id, owerite=True)
    print(res)
    res_url = cloudinary.CloudinaryImage(public_id).build_url(
        width=250, height=250, crop="fill", version=res.get("version")
    )
    user = await reps_users.update_avatar_url(user.email, res_url, db)
    auth_service.cache.set(user.email, pickle.dumps(user))
    auth_service.cache.expire(user.email, 300)

    return user