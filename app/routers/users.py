from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..errors import NotFound, Conflict
from ..models import User
from ..schemas import UserCreate, UserOut, Deposit, ErrorOut

router = APIRouter(prefix="/users", tags=["Users"])


def get_user_or_404(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise NotFound(f"Пользователь с id={user_id} не найден", "USER_NOT_FOUND")
    return user


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED,
             responses={409: {"model": ErrorOut}})
def create_user(data: UserCreate, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.email == data.email)):
        raise Conflict(f"Email {data.email} уже зарегистрирован", "EMAIL_ALREADY_EXISTS")
    user = User(name=data.name, email=data.email, balance=0.0)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/{user_id}", response_model=UserOut, responses={404: {"model": ErrorOut}})
def get_user(user_id: int, db: Session = Depends(get_db)):
    return get_user_or_404(db, user_id)


@router.patch("/{user_id}/deposit", response_model=UserOut, responses={404: {"model": ErrorOut}})
def deposit(user_id: int, data: Deposit, db: Session = Depends(get_db)):
    user = get_user_or_404(db, user_id)
    user.balance = round(user.balance + data.amount, 2)
    db.commit()
    db.refresh(user)
    return user
