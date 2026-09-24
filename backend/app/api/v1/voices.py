from typing import Literal
from fastapi import APIRouter, Query
from ...schemas.voices import VoicesResponse
from ...services.voice_service import voice_service

router = APIRouter(tags=['voices'])


@router.get('/voices', response_model=VoicesResponse)
def voices(engine: Literal['edge', 'kokoro'] = Query(...)) -> VoicesResponse:
    return voice_service.voices(engine)
