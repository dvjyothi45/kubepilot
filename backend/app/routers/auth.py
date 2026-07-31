from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.user import (
    UserCreate,
    UserResponse,
    UserLogin,
    Token,
)
from app.services.user_service import (
    create_user,
    get_user_by_email,
    get_user_by_username,
    authenticate_user,
)
from app.auth.jwt_handler import create_access_token

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post("/register", response_model=UserResponse)
def register(user: UserCreate, db: Session = Depends(get_db)):

    if get_user_by_email(db, user.email):
        raise HTTPException(
            status_code=400,
            detail="Email already registered",
        )

    if get_user_by_username(db, user.username):
        raise HTTPException(
            status_code=400,
            detail="Username already taken",
        )

    return create_user(db, user)


@router.post("/login", response_model=Token)
def login(user: UserLogin, db: Session = Depends(get_db)):

    db_user = authenticate_user(
        db,
        user.email,
        user.password,
    )

    if not db_user:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )

    access_token = create_access_token(
        data={
            "sub": db_user.email,
            "user_id": db_user.id,
        }
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }