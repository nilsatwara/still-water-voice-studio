"""Server-owned request identity used by authorization dependencies."""
from dataclasses import dataclass, field
from typing import Protocol
import uuid

from fastapi import Request


@dataclass(frozen=True, slots=True)
class Principal:
    user_id: uuid.UUID
    roles: frozenset[str] = field(default_factory=frozenset)
    permissions: frozenset[str] = field(default_factory=frozenset)
    active: bool = True

    def can(self, permission: str) -> bool:
        return self.active and (permission in self.permissions or '*' in self.permissions)


class IdentityResolver(Protocol):
    async def resolve(self, request: Request) -> Principal | None: ...


class AnonymousIdentityResolver:
    """Secure default until a signed session/token resolver is introduced."""

    async def resolve(self, request: Request) -> Principal | None:
        return None
