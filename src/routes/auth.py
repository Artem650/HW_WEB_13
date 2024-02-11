from fastapi import APIRouter, HTTPException, Request, Depends, status, Path, Query, Security, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm, HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.db import get_db
from src.repository import users as reps_users
from src.schemas.user import UserSchema, TokenSchema, UserResponse, RequestEmail
from src.services.auth import auth_service
from src.services.email import send_email, send_email_reset_password

import re
from datetime import date, timedelta

router = APIRouter(prefix='/auth', tags=['auth'])
get_refresh_token = HTTPBearer()


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)

async def signup(body: UserSchema, bt: BackgroundTasks, request: Request, db: AsyncSession = Depends(get_db)):

    exist_user = await reps_users.get_user_by_email(body.email, db)
    if exist_user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Account already exists")
    body.password = auth_service.get_password_hash(body.password)
    new_user = await reps_users.create_user(body, db)
    bt.add_task(send_email, new_user.email, new_user.username, str(request.base_url))
    return new_user


@router.post("/login", response_model=TokenSchema)

async def login(body: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):

    user = await reps_users.get_user_by_email(body.username, db)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email")
    if not user.confirmation:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email not confirmed")
    if not auth_service.verify_password(body.password, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password")

    access_token = await auth_service.create_access_token(data={"sub": user.email, "test": "Ярослав Вдовенко"})
    refresh_token = await auth_service.create_refresh_token(data={"sub": user.email})
    await reps_users.update_token(user, refresh_token, db)
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


@router.get('/refresh_token', response_model=TokenSchema)

async def refresh_token(credentials: HTTPAuthorizationCredentials = Depends(get_refresh_token),
                        db: AsyncSession = Depends(get_db)):

    token = credentials.credentials
    email = await auth_service.decode_refresh_token(token)
    user = await reps_users.get_user_by_email(email, db)
    if user.refresh_token != token:
        await reps_users.update_token(user, None, db)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    access_token = await auth_service.create_access_token(data={"sub": email})
    refresh_token = await auth_service.create_refresh_token(data={"sub": email})
    await reps_users.update_token(user, refresh_token, db)
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


@router.get('/confirmed_email/{token}')
async def confirmed_email(token: str, db: AsyncSession = Depends(get_db)):

    email = await auth_service.get_email_from_token(token)
    user = await reps_users.get_user_by_email(email, db)
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Verification error")
    if user.confirmation:
        return {"message": "Your email is already confirmed"}
    await reps_users.confirmed_email(email, db)
    return {"message": "Email confirmed"}


@router.post('/request_email')
async def request_email(body: RequestEmail, background_tasks: BackgroundTasks, request: Request,
                        db: AsyncSession = Depends(get_db)):

    user = await reps_users.get_user_by_email(body.email, db)

    if user.confirmation:
        return {"message": "Your email is already confirmed"}
    if user:
        background_tasks.add_task(send_email, user.email, user.username, str(request.base_url))
    return {"message": "Check your email for confirmation."}



@router.post("/forget-password")
async def forget_password(
        background_tasks: BackgroundTasks,
        fpr: RequestEmail,
        request: Request,
        db: AsyncSession = Depends(get_db)
):
    try:
        user = await reps_users.get_user_by_email(fpr.email, db)
        print('-----------------------')
        print(user.email, user.username)
        if user is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                detail="Invalid Email address")

        '''forget_url_link =  f"{config.APP_HOST}{settings.FORGET_PASSWORD_URL}/{secret_token}"

        email_body = { "company_name": settings.MAIL_FROM_NAME,
                       "link_expiry_min": settings.FORGET_PASSWORD_LINK_EXPIRE_MINUTES,
                       "reset_link": forget_url_link }

        message = MessageSchema(
            subject="Password Reset Instructions",
            recipients=[fpr.email],
            template_body=email_body,
            subtype=MessageType.html
          )

        template_name = "mail/password_reset.html"

        fm = FastMail(mail_conf)
        background_tasks.add_task(fm.send_message, message, template_name)'''
        background_tasks.add_task(send_email_reset_password, user.email, user.username, str(request.base_url))
        return JSONResponse(status_code=status.HTTP_200_OK,
                            content={"message": "Email has been sent", "success": True,
                                     "status_code": status.HTTP_200_OK})
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Something Unexpected, Server Error")