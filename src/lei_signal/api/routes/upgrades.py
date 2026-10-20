"""系统待升级目标的单用户本地管理接口；不会启动后台工作。"""
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from lei_signal.api import config, upgrades_store as store
from lei_signal.api.upgrade_models import GoalAction, GoalCreate, GoalPatch

router = APIRouter(prefix="/api/upgrades", tags=["upgrades"])


def _paths(request):
    path = getattr(request.app.state, "upgrades_db_path", None) or os.environ.get(
        "LEI_UPGRADES_DB", str(Path(config.sqlite_path()).with_name("system_upgrades.db")))
    seed = getattr(request.app.state, "upgrades_seed_path", store.SEED_PATH)
    return path, seed


def _call(fn, request, *args):
    path, seed = _paths(request)
    try:
        return fn(path, *args, seed_path=seed)
    except store.GoalError as exc:
        raise HTTPException(exc.status, str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(422, "目标内容不符合要求，请检查字段长度、日期和完成标准") from exc


@router.get("")
def list_goals(request: Request):
    return _call(store.list_goals, request)


@router.get("/export")
def export_goals(request: Request):
    data = _call(store.list_goals, request)
    return JSONResponse({"schema_version": 1, **data}, headers={
        "Content-Disposition": 'attachment; filename="system-upgrades.json"',
        "Cache-Control": "no-store"})


@router.post("", status_code=201)
def create_goal(body: GoalCreate, request: Request):
    return _call(store.create_goal, request, body.model_dump(mode="json"))


@router.patch("/{key}")
def patch_goal(key: str, body: GoalPatch, request: Request):
    return _call(store.patch_goal, request, key, body.model_dump(mode="json", exclude_unset=True))


@router.post("/{key}/actions")
def act_on_goal(key: str, body: GoalAction, request: Request):
    return _call(store.act_on_goal, request, key, body.model_dump(mode="json"))
