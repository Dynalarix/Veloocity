from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import Rental

engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                       poolclass=StaticPool)
TestingSession = sessionmaker(bind=engine)


def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield


client = TestClient(app)


def shift_rental_start(rental_id: int, minutes: int):
    db = TestingSession()
    r = db.get(Rental, rental_id)
    r.start_time -= timedelta(minutes=minutes)
    db.commit()
    db.close()


def setup_world():
    u = client.post("/users", json={"name": "Иван", "email": "ivan@mail.ru"}).json()
    s = client.post("/stations", json={"name": "Центр", "location": "ул. Ленина, 1"}).json()
    b = client.post("/bikes", json={"model": "Stels 700", "station_id": s["id"]}).json()
    return u, s, b


def test_users():
    r = client.post("/users", json={"name": "Иван", "email": "ivan@mail.ru"})
    assert r.status_code == 201 and r.json()["balance"] == 0.0
    r = client.post("/users", json={"name": "Другой", "email": "ivan@mail.ru"})
    assert r.status_code == 409 and r.json()["error_code"] == "EMAIL_ALREADY_EXISTS"
    assert client.get("/users/999").json()["error_code"] == "USER_NOT_FOUND"
    r = client.patch("/users/1/deposit", json={"amount": 500})
    assert r.status_code == 200 and r.json()["balance"] == 500
    assert client.patch("/users/1/deposit", json={"amount": -5}).status_code == 422


def test_stations_and_bikes_filter():
    _, s, _ = setup_world()
    client.post("/bikes", json={"model": "Forward", "station_id": s["id"], "status": "broken"})
    s2 = client.post("/stations", json={"name": "Парк", "location": "Парк Горького"}).json()
    client.post("/bikes", json={"model": "Merida", "station_id": s2["id"]})

    st = client.get("/stations").json()
    assert st[0]["available_bikes"] == 1 and st[1]["available_bikes"] == 1

    assert len(client.get("/bikes").json()) == 3
    assert len(client.get(f"/bikes?station_id={s['id']}").json()) == 2
    assert len(client.get(f"/bikes?station_id={s['id']}&status=broken").json()) == 1
    assert client.get("/bikes?status=flying").status_code == 422
    r = client.post("/bikes", json={"model": "X", "station_id": 999})
    assert r.status_code == 404 and r.json()["error_code"] == "STATION_NOT_FOUND"


def test_rental_flow_paid():
    u, _, b = setup_world()
    client.patch(f"/users/{u['id']}/deposit", json={"amount": 300})
    r = client.post("/rentals/start", json={"user_id": u["id"], "bike_id": b["id"]})
    assert r.status_code == 201
    rid = r.json()["id"]
    assert client.get(f"/bikes?status=rented").json()[0]["id"] == b["id"]

    r = client.post("/rentals/start", json={"user_id": u["id"], "bike_id": b["id"]})
    assert r.status_code == 409 and r.json()["error_code"] == "BIKE_ALREADY_RENTED"

    shift_rental_start(rid, 90)  # 1.5 часа -> 2 часа -> 200 руб.
    r = client.post("/rentals/end", json={"rental_id": rid})
    assert r.status_code == 200 and r.json()["total_cost"] == 200
    assert client.get(f"/users/{u['id']}").json()["balance"] == 100
    assert client.get("/bikes?status=available").json()[0]["id"] == b["id"]

    r = client.post("/rentals/end", json={"rental_id": rid})
    assert r.status_code == 409 and r.json()["error_code"] == "RENTAL_ALREADY_FINISHED"
    assert len(client.get(f"/rentals/{u['id']}").json()) == 1


def test_rental_insufficient_funds():
    u, _, b = setup_world()
    rid = client.post("/rentals/start", json={"user_id": u["id"], "bike_id": b["id"]}).json()["id"]
    r = client.post("/rentals/end", json={"rental_id": rid})
    assert r.status_code == 400 and r.json()["error_code"] == "INSUFFICIENT_FUNDS"
    # аренда всё равно завершена, баланс в минусе, велосипед свободен
    assert client.get(f"/users/{u['id']}").json()["balance"] == -100
    hist = client.get(f"/rentals/{u['id']}").json()
    assert hist[0]["end_time"] is not None
    assert client.get("/bikes?status=available").json()[0]["id"] == b["id"]
    # с долгом новую аренду не начать
    r = client.post("/rentals/start", json={"user_id": u["id"], "bike_id": b["id"]})
    assert r.status_code == 400 and r.json()["error_code"] == "INSUFFICIENT_FUNDS"


def test_rental_errors():
    u, s, _ = setup_world()
    broken = client.post("/bikes", json={"model": "F", "station_id": s["id"], "status": "broken"}).json()
    r = client.post("/rentals/start", json={"user_id": u["id"], "bike_id": broken["id"]})
    assert r.status_code == 400 and r.json()["error_code"] == "BIKE_BROKEN"
    r = client.post("/rentals/start", json={"user_id": 999, "bike_id": 1})
    assert r.status_code == 404 and r.json()["error_code"] == "USER_NOT_FOUND"
    r = client.post("/rentals/start", json={"user_id": u["id"], "bike_id": 999})
    assert r.status_code == 404 and r.json()["error_code"] == "BIKE_NOT_FOUND"
    r = client.post("/rentals/end", json={"rental_id": 999})
    assert r.status_code == 404 and r.json()["error_code"] == "RENTAL_NOT_FOUND"
    assert client.get("/rentals/999").status_code == 404
