"""Reusable FastAPI authentication and permission guards."""
from collections.abc import Callable
import re

from fastapi import Depends, HTTPException, Request, status

from ..core.security import Principal


PERMISSION_PATTERN = re.compile(r'^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+$')


def current_principal(request: Request) -> Principal:
    principal = getattr(request.state, 'principal', None)
    if not isinstance(principal, Principal):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Authentication is required.',
            headers={'WWW-Authenticate': 'Bearer'},
        )
    if not principal.active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='This account is not active.')
    return principal


def require_permission(permission: str) -> Callable:
    if not PERMISSION_PATTERN.fullmatch(permission):
        raise ValueError(f'Invalid permission code: {permission!r}')

    def permission_guard(principal: Principal = Depends(current_principal)) -> Principal:
        if not principal.can(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='You do not have permission to perform this action.',
            )
        return principal

    return permission_guard


def require_any_permission(*permissions: str) -> Callable:
    if not permissions:
        raise ValueError('At least one permission is required.')
    for permission in permissions:
        if not PERMISSION_PATTERN.fullmatch(permission):
            raise ValueError(f'Invalid permission code: {permission!r}')

    def permission_guard(principal: Principal = Depends(current_principal)) -> Principal:
        if not any(principal.can(permission) for permission in permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='You do not have permission to perform this action.',
            )
        return principal

    return permission_guard
