from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
from db import AsyncSessionLocal, init_db
from sqlalchemy.ext.asyncio import AsyncSession
import logging
from api import router
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.requests import Request as StarletteRequest
from logging_config import configure_logging, request_id_var

# Configure logging with requestId support
configure_logging()
logger = logging.getLogger("paynow")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(lifespan=lifespan)

# Exception handler for validation errors


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
        request: StarletteRequest,
        exc: RequestValidationError):
    try:
        body = await request.body()
    except Exception:
        body = b"<could not read body>"
    logger.error(
        f"Validation error for path {
            request.url.path}: {
            exc.errors()} | Body: {
                body.decode(
                    'utf-8',
                    'ignore')}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )

# Database dependency


async def get_db():
    async with AsyncSessionLocal() as db:
        yield db

# Middleware to set request_id into contextvars for all requests
@app.middleware("http")
async def add_request_id_to_logs(request: Request, call_next):
    # Try to carry request_id if provided; otherwise generate
    header_req_id = request.headers.get("X-Request-Id")
    req_id = header_req_id or f"req_{logging.uuid4().hex[:8]}" if hasattr(logging, 'uuid4') else None
    # Fallback to short random if uuid not on logging
    if req_id is None:
        import uuid as _uuid
        req_id = f"req_{_uuid.uuid4().hex[:8]}"
    token = request_id_var.set(req_id)
    try:
        response = await call_next(request)
    finally:
        request_id_var.reset(token)
    # Echo request id back for clients
    response.headers["X-Request-Id"] = req_id
    return response

# Include the API router
app.include_router(router)
