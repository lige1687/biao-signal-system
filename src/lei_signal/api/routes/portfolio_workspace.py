"""Today holdings workspace endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

from lei_signal.api.portfolio_workspace import build_workspace, link_plan

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


class LinkPlanRequest(BaseModel):
    plan_id: str


@router.get("/workspace")
def get_workspace(request: Request) -> dict:
    return build_workspace(request)


@router.put("/holdings/{holding_id}/plan")
def put_holding_plan(request: Request, holding_id: str, body: LinkPlanRequest) -> dict:
    return link_plan(request, holding_id, body.plan_id)
