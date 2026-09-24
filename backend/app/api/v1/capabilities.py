from fastapi import APIRouter
from ...schemas.capabilities import CapabilitiesResponse
from ...services.voice_service import voice_service

router = APIRouter(tags=['capabilities'])


@router.get('/capabilities', response_model=CapabilitiesResponse)
def capabilities() -> CapabilitiesResponse:
    return voice_service.capabilities()
