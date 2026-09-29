import math
from datetime import datetime

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..errors import NotFound, Conflict, BadRequest
from ..models import Bike, BikeStatus, Rental
from ..schemas import RentalStart, RentalEnd, RentalOut, ErrorOut
from .users import get_user_or_404

router = APIRouter(prefix="/rentals", tags=["Rentals"])

PRICE_PER_HOUR = 100.0  # руб. за каждый час или неполный час


def calc_cost(start: datetime, end: datetime) -> float:
    seconds = max((end - start).total_seconds(), 0)
    hours = max(1, math.ceil(seconds / 3600))  # минимум 1 час
    return hours * PRICE_PER_HOUR


@router.post("/start", response_model=RentalOut, status_code=status.HTTP_201_CREATED,
             responses={400: {"model": ErrorOut}, 404: {"model": ErrorOut}, 409: {"model": ErrorOut}})
def start_rental(data: RentalStart, db: Session = Depends(get_db)):
    user = get_user_or_404(db, data.user_id)

    bike = db.get(Bike, data.bike_id)
    if bike is None:
        raise NotFound(f"Велосипед с id={data.bike_id} не найден", "BIKE_NOT_FOUND")
    if bike.status == BikeStatus.broken:
        raise BadRequest("Велосипед сломан и недоступен для аренды", "BIKE_BROKEN")
    if bike.status == BikeStatus.rented:
        raise Conflict("Велосипед уже арендован", "BIKE_ALREADY_RENTED")

    if user.balance < 0:
        raise BadRequest("Отрицательный баланс: пополните счёт перед новой арендой",
                         "INSUFFICIENT_FUNDS")

    active = db.scalar(select(Rental).where(Rental.user_id == user.id,
                                            Rental.end_time.is_(None)))
    if active:
        raise Conflict(f"У пользователя уже есть активная аренда id={active.id}",
                       "ACTIVE_RENTAL_EXISTS")

    bike.status = BikeStatus.rented
    rental = Rental(user_id=user.id, bike_id=bike.id,
                    start_time=datetime.utcnow(), total_cost=0.0)
    db.add(rental)
    db.commit()
    db.refresh(rental)
    return rental


@router.post("/end", response_model=RentalOut,
             responses={400: {"model": ErrorOut}, 404: {"model": ErrorOut}, 409: {"model": ErrorOut}})
def end_rental(data: RentalEnd, db: Session = Depends(get_db)):
    rental = db.get(Rental, data.rental_id)
    if rental is None:
        raise NotFound(f"Аренда с id={data.rental_id} не найдена", "RENTAL_NOT_FOUND")
    if rental.end_time is not None:
        raise Conflict("Аренда уже завершена", "RENTAL_ALREADY_FINISHED")

    rental.end_time = datetime.utcnow()
    rental.total_cost = calc_cost(rental.start_time, rental.end_time)

    user = rental.user
    enough_money = user.balance >= rental.total_cost
    user.balance = round(user.balance - rental.total_cost, 2)  # может уйти в минус
    rental.bike.status = BikeStatus.available

    db.commit()  # аренда завершается в любом случае
    db.refresh(rental)

    if not enough_money:
        raise BadRequest(
            f"Недостаточно средств: списано {rental.total_cost:.2f} руб., "
            f"баланс {user.balance:.2f} руб. Аренда id={rental.id} завершена.",
            "INSUFFICIENT_FUNDS",
        )
    return rental


@router.get("/{user_id}", response_model=list[RentalOut], responses={404: {"model": ErrorOut}})
def rental_history(user_id: int, db: Session = Depends(get_db)):
    get_user_or_404(db, user_id)
    return db.scalars(select(Rental).where(Rental.user_id == user_id)
                      .order_by(Rental.start_time.desc())).all()
