from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from .models import BikeStatus


# ---------- Users ----------
class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: EmailStr
    balance: float


class Deposit(BaseModel):
    amount: float = Field(gt=0, description="Сумма пополнения, > 0")


# ---------- Stations ----------
class StationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    location: str = Field(min_length=1, max_length=255)


class StationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    location: str


class StationWithCount(StationOut):
    available_bikes: int


# ---------- Bikes ----------
class BikeCreate(BaseModel):
    model: str = Field(min_length=1, max_length=100)
    station_id: int
    status: BikeStatus = BikeStatus.available


class BikeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    model: str
    station_id: int
    status: BikeStatus


# ---------- Rentals ----------
class RentalStart(BaseModel):
    user_id: int
    bike_id: int


class RentalEnd(BaseModel):
    rental_id: int


class RentalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    bike_id: int
    start_time: datetime
    end_time: Optional[datetime] = None
    total_cost: float


# ---------- Errors ----------
class ErrorOut(BaseModel):
    detail: str
    error_code: str
