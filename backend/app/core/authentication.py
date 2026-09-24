"""Populate request identity through a trusted server-side resolver."""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from .security import AnonymousIdentityResolver, IdentityResolver


class AuthenticationContextMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, resolver: IdentityResolver | None = None):
        super().__init__(app)
        self._default_resolver = resolver or AnonymousIdentityResolver()

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Never derive identity from X-User, X-Role, or similar client headers.
        resolver: IdentityResolver = getattr(
            request.app.state,
            'identity_resolver',
            self._default_resolver,
        )
        request.state.principal = await resolver.resolve(request)
        return await call_next(request)
