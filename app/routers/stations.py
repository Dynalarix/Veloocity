from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select, func, case
from sqlalchemy.orm import Session

from ..database import get_db
from ..errors import NotFound
from ..models import Station, Bike, BikeStatus
from ..schemas import (StationCreate, StationOut, StationWithCount,
                       BikeCreate, BikeOut, ErrorOut)

stations_router = APIRouter(prefix="/stations", tags=["Stations"])
bikes_router = APIRouter(prefix="/bikes", tags=["Bikes"])


@stations_router.post("", response_model=StationOut, status_code=status.HTTP_201_CREATED)
def create_station(data: StationCreate, db: Session = Depends(get_db)):
    station = Station(name=data.name, location=data.location)
    db.add(station)
    db.commit()
    db.refresh(station)
    return station


@stations_router.get("", response_model=list[StationWithCount])
def list_stations(db: Session = Depends(get_db)):
    available = func.count(case((Bike.status == BikeStatus.available, Bike.id)))
    rows = db.execute(
        select(Station, available.label("available_bikes"))
        .outerjoin(Bike, Bike.station_id == Station.id)
        .group_by(Station.id)
        .order_by(Station.id)
    ).all()
    return [
        StationWithCount(id=s.id, name=s.name, location=s.location, available_bikes=cnt)
        for s, cnt in rows
    ]


@bikes_router.post("", response_model=BikeOut, status_code=status.HTTP_201_CREATED,
                   responses={404: {"model": ErrorOut}})
def create_bike(data: BikeCreate, db: Session = Depends(get_db)):
    if db.get(Station, data.station_id) is None:
        raise NotFound(f"Станция с id={data.station_id} не найдена", "STATION_NOT_FOUND")
    bike = Bike(model=data.model, station_id=data.station_id, status=data.status)
    db.add(bike)
    db.commit()
    db.refresh(bike)
    return bike


@bikes_router.get("", response_model=list[BikeOut])
def list_bikes(
    station_id: Optional[int] = Query(None, description="Фильтр по станции"),
    status: Optional[BikeStatus] = Query(None, description="Фильтр по статусу"),
    db: Session = Depends(get_db),
):
    stmt = select(Bike).order_by(Bike.id)
    if station_id is not None:
        stmt = stmt.where(Bike.station_id == station_id)
    if status is not None:
        stmt = stmt.where(Bike.status == status)
    return db.scalars(stmt).all()
