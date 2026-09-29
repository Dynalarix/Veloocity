from fastapi import FastAPI

from .database import Base, engine
from .errors import APIError, api_error_handler
from .routers import users, stations, rentals

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="VelooCity API",
    description="REST API сервиса шеринга велосипедов",
    version="1.0.0",
)

app.add_exception_handler(APIError, api_error_handler)

app.include_router(users.router)
app.include_router(stations.stations_router)
app.include_router(stations.bikes_router)
app.include_router(rentals.router)


@app.get("/", tags=["Health"])
def root():
    return {"service": "VelooCity", "docs": "/docs"}
