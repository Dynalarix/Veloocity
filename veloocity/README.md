# VelooCity API

REST API сервиса шеринга велосипедов (FastAPI + SQLAlchemy 2.0 + SQLite + Pydantic v2).

## Запуск

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Swagger UI: http://127.0.0.1:8000/docs

Через Docker:

```bash
docker build -t veloocity .
docker run -p 8000:8000 veloocity
```

## Тесты

```bash
pytest -v
```

## Структура

```
app/
  main.py          — приложение, подключение роутеров и обработчика ошибок
  database.py      — движок SQLAlchemy, сессия, get_db
  models.py        — User, Station, Bike, Rental, BikeStatus
  schemas.py       — Pydantic-схемы запросов/ответов
  errors.py        — кастомные исключения и единый формат ошибок
  routers/
    users.py       — /users
    stations.py    — /stations, /bikes
    rentals.py     — /rentals
tests/test_api.py  — тесты всех сценариев
```

## Эндпоинты

| Метод | Путь | Описание | Коды |
|---|---|---|---|
| POST | /users | Регистрация | 201, 409, 422 |
| GET | /users/{user_id} | Пользователь | 200, 404 |
| PATCH | /users/{user_id}/deposit | Пополнение баланса `{"amount": 500}` | 200, 404, 422 |
| POST | /stations | Создать станцию | 201, 422 |
| GET | /stations | Станции + `available_bikes` | 200 |
| POST | /bikes | Добавить велосипед | 201, 404, 422 |
| GET | /bikes?station_id=&status= | Список с фильтрами | 200, 422 |
| POST | /rentals/start | Начать аренду `{"user_id", "bike_id"}` | 201, 400, 404, 409 |
| POST | /rentals/end | Завершить аренду `{"rental_id"}` | 200, 400, 404, 409 |
| GET | /rentals/{user_id} | История аренд | 200, 404 |

## Бизнес-правила

- Тариф: 100 руб. за каждый начатый час (минимум 1 час).
- При завершении аренды, если денег не хватает, аренда всё равно завершается,
  баланс уходит в минус, велосипед становится `available`, а API возвращает
  `400 INSUFFICIENT_FUNDS`.
- С отрицательным балансом новую аренду начать нельзя (`400 INSUFFICIENT_FUNDS`).
- У пользователя может быть только одна активная аренда (`409 ACTIVE_RENTAL_EXISTS`).

## Формат ошибок

```json
{"detail": "Велосипед уже арендован", "error_code": "BIKE_ALREADY_RENTED"}
```

Коды: `USER_NOT_FOUND`, `BIKE_NOT_FOUND`, `STATION_NOT_FOUND`, `RENTAL_NOT_FOUND`,
`EMAIL_ALREADY_EXISTS`, `BIKE_ALREADY_RENTED`, `ACTIVE_RENTAL_EXISTS`,
`RENTAL_ALREADY_FINISHED`, `BIKE_BROKEN`, `INSUFFICIENT_FUNDS`.
