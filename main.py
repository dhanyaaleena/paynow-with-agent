from fastapi import FastAPI
from contextlib import asynccontextmanager
from db import AsyncSessionLocal, init_db
from sqlalchemy.ext.asyncio import AsyncSession
import logging
from api import router
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.requests import Request as StarletteRequest

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s')
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

# Include the API router
app.include_router(router)
