"""Load effective permissions from normalized role assignments."""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..core.security import Principal
from ..models import Role, User


def user_with_permissions_statement(user_id: uuid.UUID):
    return (
        select(User)
        .where(User.id == user_id)
        .options(selectinload(User.roles).selectinload(Role.permissions))
    )


class RBACService:
    async def principal_for_user(self, session: AsyncSession, user_id: uuid.UUID) -> Principal | None:
        user = await session.scalar(user_with_permissions_statement(user_id))
        if user is None:
            return None
        roles = frozenset(role.name for role in user.roles if role.status == 'active')
        permissions = frozenset(
            permission.code
            for role in user.roles
            if role.status == 'active'
            for permission in role.permissions
        )
        return Principal(
            user_id=user.id,
            roles=roles,
            permissions=permissions,
            active=user.status == 'active',
        )


rbac_service = RBACService()
