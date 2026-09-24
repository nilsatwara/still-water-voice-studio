from pydantic import BaseModel, ConfigDict


class AdminAccessResponse(BaseModel):
    model_config = ConfigDict(extra='forbid')

    authorized: bool
