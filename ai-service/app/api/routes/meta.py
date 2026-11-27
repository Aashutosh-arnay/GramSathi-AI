"""GET /api/v1/meta/states – canonical Indian states and union territories."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.security import require_api_key
from app.core.states import CANONICAL_STATES

router = APIRouter(
    prefix="/api/v1/meta",
    tags=["Metadata"],
    dependencies=[Depends(require_api_key)],
)


class StatesResponse(BaseModel):
    states: list[str]
    count: int


@router.get(
    "/states",
    response_model=StatesResponse,
    summary="List canonical Indian states and union territories",
    description="Returns the canonical list of 28 states and 8 union territories.",
)
async def list_states() -> StatesResponse:
    return StatesResponse(
        states=list(CANONICAL_STATES),
        count=len(CANONICAL_STATES),
    )
