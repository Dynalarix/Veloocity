from fastapi import Request
from fastapi.responses import JSONResponse


class APIError(Exception):
    """Базовое кастомное исключение API."""

    def __init__(self, status_code: int, detail: str, error_code: str):
        self.status_code = status_code
        self.detail = detail
        self.error_code = error_code


class NotFound(APIError):
    def __init__(self, detail: str, error_code: str):
        super().__init__(404, detail, error_code)


class Conflict(APIError):
    def __init__(self, detail: str, error_code: str):
        super().__init__(409, detail, error_code)


class BadRequest(APIError):
    def __init__(self, detail: str, error_code: str):
        super().__init__(400, detail, error_code)


async def api_error_handler(request: Request, exc: APIError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "error_code": exc.error_code},
    )
