"""Start the sidecar using APP_HOST and APP_PORT configuration."""
import uvicorn
from .core.config import settings


if __name__ == '__main__':
    uvicorn.run('backend.app.main:app', host=settings.host, port=settings.port)
