"""Environment-backed configuration for the isolated FastAPI sidecar."""
from dataclasses import dataclass, field
import os
from pathlib import Path


def _origins(value: str) -> tuple[str, ...]:
    origins = tuple(dict.fromkeys(origin.strip().rstrip('/') for origin in value.split(',') if origin.strip()))
    if '*' in origins:
        raise ValueError('CORS_ORIGINS must contain explicit origins; wildcard access is disabled.')
    return origins


def _integer(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError as exc:
        raise ValueError(f'{name} must be an integer.') from exc
    if not minimum <= value <= maximum:
        raise ValueError(f'{name} must be between {minimum} and {maximum}.')
    return value


def _database_url(value: str | None) -> str | None:
    if not value or not value.strip():
        return None
    url = value.strip()
    if url.startswith('postgres://'):
        url = 'postgresql+psycopg://' + url.removeprefix('postgres://')
    elif url.startswith('postgresql://'):
        url = 'postgresql+psycopg://' + url.removeprefix('postgresql://')
    if not url.startswith('postgresql+psycopg://'):
        raise ValueError('DATABASE_URL must use PostgreSQL with the psycopg driver.')
    return url


@dataclass(frozen=True)
class Settings:
    host: str
    port: int
    api_prefix: str
    cors_origins: tuple[str, ...]
    database_url: str | None = field(default=None, repr=False)
    cache_url: str | None = field(default=None, repr=False)
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_timeout: int = 30
    db_pool_recycle: int = 1800
    media_storage_root: Path = Path('backend/app/storage/generated/media')
    media_max_bytes: int = 10 * 1024 * 1024
    turnstile_secret_key: str | None = field(default=None, repr=False)

    @classmethod
    def from_env(cls) -> "Settings":
        prefix = os.getenv('API_PREFIX', '/api/v1').strip()
        if not prefix.startswith('/'):
            prefix = '/' + prefix
        prefix = prefix.rstrip('/') or '/api/v1'
        try:
            port = int(os.getenv('APP_PORT', '8767'))
        except ValueError as exc:
            raise ValueError('APP_PORT must be an integer.') from exc
        if not 1 <= port <= 65535:
            raise ValueError('APP_PORT must be between 1 and 65535.')
        return cls(
            host=os.getenv('APP_HOST', '127.0.0.1').strip() or '127.0.0.1',
            port=port,
            api_prefix=prefix,
            cors_origins=_origins(os.getenv(
                'CORS_ORIGINS',
                'http://127.0.0.1:8766,http://localhost:8766,http://127.0.0.1:3000,http://localhost:3000',
            )),
            database_url=_database_url(os.getenv('DATABASE_URL')),
            cache_url=os.getenv('CACHE_URL') or None,
            db_pool_size=_integer('DB_POOL_SIZE', 5, 1, 100),
            db_max_overflow=_integer('DB_MAX_OVERFLOW', 10, 0, 200),
            db_pool_timeout=_integer('DB_POOL_TIMEOUT', 30, 1, 300),
            db_pool_recycle=_integer('DB_POOL_RECYCLE', 1800, 60, 86400),
            media_storage_root=Path(os.getenv('MEDIA_STORAGE_ROOT','backend/app/storage/generated/media')),
            media_max_bytes=_integer('MEDIA_MAX_BYTES',10*1024*1024,1024,100*1024*1024),
            turnstile_secret_key=os.getenv('TURNSTILE_SECRET_KEY') or None,
        )


settings = Settings.from_env()
