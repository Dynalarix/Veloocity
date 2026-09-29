import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Float, ForeignKey, DateTime, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class BikeStatus(str, enum.Enum):
    available = "available"
    rented = "rented"
    broken = "broken"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    balance: Mapped[float] = mapped_column(Float, default=0.0)

    rentals: Mapped[list["Rental"]] = relationship(back_populates="user")


class Station(Base):
    __tablename__ = "stations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    location: Mapped[str] = mapped_column(String(255))

    bikes: Mapped[list["Bike"]] = relationship(back_populates="station")


class Bike(Base):
    __tablename__ = "bikes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    model: Mapped[str] = mapped_column(String(100))
    station_id: Mapped[int] = mapped_column(ForeignKey("stations.id"))
    status: Mapped[BikeStatus] = mapped_column(Enum(BikeStatus), default=BikeStatus.available)

    station: Mapped["Station"] = relationship(back_populates="bikes")
    rentals: Mapped[list["Rental"]] = relationship(back_populates="bike")


class Rental(Base):
    __tablename__ = "rentals"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    bike_id: Mapped[int] = mapped_column(ForeignKey("bikes.id"))
    start_time: Mapped[datetime] = mapped_column(DateTime)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    total_cost: Mapped[float] = mapped_column(Float, default=0.0)

    user: Mapped["User"] = relationship(back_populates="rentals")
    bike: Mapped["Bike"] = relationship(back_populates="rentals")
