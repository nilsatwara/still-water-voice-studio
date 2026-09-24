from fastapi import APIRouter, Depends

from ...api.dependencies import require_permission
from ...core.security import Principal
from ...schemas.admin import AdminAccessResponse


router = APIRouter(prefix='/admin', tags=['admin'])


@router.get('/access', response_model=AdminAccessResponse)
def admin_access(
    _: Principal = Depends(require_permission('admin.access')),
) -> AdminAccessResponse:
    return AdminAccessResponse(authorized=True)
