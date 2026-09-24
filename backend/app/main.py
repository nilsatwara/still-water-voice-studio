"""Isolated FastAPI sidecar. It does not own synthesis or the legacy queue."""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from .api.v1.router import router as v1_router
from .core.config import settings
from .core.database import database
from .core.authentication import AuthenticationContextMiddleware

logger = logging.getLogger('tts_api')


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    await database.dispose()

app = FastAPI(
    title='Stillwater TTS API',
    version='1.0.0',
    docs_url='/docs',
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(AuthenticationContextMiddleware)

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=False,
        allow_methods=['GET'],
        allow_headers=['Accept', 'Content-Type'],
    )


@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    logger.exception('Unhandled API error on %s', request.url.path, exc_info=exc)
    return JSONResponse(status_code=500, content={'detail': 'The API could not complete this request.'})


app.include_router(v1_router, prefix=settings.api_prefix)
