"""自选股与分组端点。

分组语义见 api/watchlist 模块文档：内置「大盘」组不入库（config 常量），
用户自建组可增删改；删组时成员转为未分组，不丢标的。
"""
from __future__ import annotations

from contextlib import closing

from fastapi import APIRouter, HTTPException, Request, Response

from lei_signal.api import config
from lei_signal.api.schemas import (
    GroupCreateRequest,
    GroupRenameRequest,
    MoveToGroupRequest,
    WatchlistAddRequest,
    WatchlistGroupDTO,
    WatchlistItemDTO,
)
from lei_signal.api.watchlist import (
    WatchlistItem,
    create_group,
    delete_group,
    delete_watchlist,
    list_groups,
    list_watchlist,
    move_to_group,
    rename_group,
    upsert_watchlist,
)
from lei_signal.data.symbols import MARKET_CN, resolve_symbol
from lei_signal.storage.sqlite_store import connect

router = APIRouter(prefix="/api", tags=["watchlist"])

#: 内置大盘组的展示名。它不是数据库记录，因此 group_id 为 None 且 builtin=True。
BUILTIN_INDEX_GROUP = "大盘"
UNGROUPED_NAME = "未分组"


def _db_path(request: Request) -> str:
    return request.app.state.watchlist_db_path


def _to_dto(item: WatchlistItem) -> WatchlistItemDTO:
    return WatchlistItemDTO(
        symbol=item.symbol,
        display_name=item.display_name,
        market=item.market,
        market_cn=MARKET_CN.get(item.market, item.market),
        note=item.note,
        sort_order=item.sort_order,
        added_at=item.added_at,
        group_id=item.group_id,
    )


@router.get("/watchlist", response_model=list[WatchlistItemDTO])
def get_watchlist(request: Request) -> list[WatchlistItemDTO]:
    with closing(connect(_db_path(request))) as conn:
        return [_to_dto(item) for item in list_watchlist(conn)]


@router.get("/sectors")
def list_sectors() -> dict[str, list[dict[str, str]]]:
    """可添加的板块/指数/ETF 清单，分三类返回。

    供前端选择器候选框使用。``sectors`` = 同花顺 90 个行业板块；
    ``indices`` = 策略/规模/主题指数（上证50、中证500、中证红利……）；
    ``us_etfs`` = 美股 ETF（宽基/行业/风格/债券商品，全部实测数据可达）。
    """
    from lei_signal.api.labels import THS_INDUSTRY_NAMES

    sectors = [
        {"code": code, "name": name, "symbol": f"TH{code}"}
        for code, name in THS_INDUSTRY_NAMES.items()
    ]
    sectors.sort(key=lambda x: x["name"])

    indices = [
        {"code": idx.symbol, "name": idx.display_name, "symbol": idx.symbol}
        for idx in config.STRATEGY_INDICES
    ]
    indices.sort(key=lambda x: x["name"])

    us_etfs = [
        {"code": etf.symbol, "name": etf.display_name, "symbol": etf.symbol}
        for etf in config.US_ETFS
    ]
    return {"sectors": sectors, "indices": indices, "us_etfs": us_etfs}


@router.post("/watchlist", response_model=WatchlistItemDTO, status_code=201)
def add_watchlist(request: Request, body: WatchlistAddRequest) -> WatchlistItemDTO:
    """添加自选。只解析符号格式，不要求行情可用（离线也要能添加）。"""
    try:
        info = resolve_symbol(body.symbol)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    with closing(connect(_db_path(request))) as conn:
        item = upsert_watchlist(
            conn,
            symbol=info.symbol,
            display_name=None,  # 名称由首次成功分析后回填展示
            market=info.market.value,
            note=body.note,
            group_id=body.group_id,
        )
    return _to_dto(item)


@router.delete("/watchlist/{symbol}", status_code=204)
def remove_watchlist(request: Request, symbol: str) -> Response:
    """删除自选（幂等）。symbol 需 URL 编码（如 %5EIXIC）。"""
    with closing(connect(_db_path(request))) as conn:
        delete_watchlist(conn, symbol)
    return Response(status_code=204)


@router.post("/watchlist/{symbol}/group", response_model=WatchlistItemDTO)
def set_item_group(
    request: Request, symbol: str, body: MoveToGroupRequest
) -> WatchlistItemDTO:
    """把标的移到指定分组；group_id 为 null 表示移出分组。"""
    with closing(connect(_db_path(request))) as conn:
        if not move_to_group(conn, symbol, body.group_id):
            raise HTTPException(status_code=404, detail=f"{symbol} 不在自选中")
        items = {i.symbol: i for i in list_watchlist(conn)}
    return _to_dto(items[symbol])


# ---------------------------------------------------------------- 分组


@router.get("/groups", response_model=list[WatchlistGroupDTO])
def get_groups(request: Request) -> list[WatchlistGroupDTO]:
    """左栏分组树：内置大盘组在最前，其后是自建组，最后是未分组（若有成员）。"""
    with closing(connect(_db_path(request))) as conn:
        groups = list_groups(conn)
        items = list_watchlist(conn)

    index_symbols = [idx.symbol for idx in config.DASHBOARD_INDICES]
    result = [
        WatchlistGroupDTO(
            group_id=None,
            name=BUILTIN_INDEX_GROUP,
            sort_order=0,
            builtin=True,
            symbols=index_symbols,
        )
    ]
    by_group: dict[int, list[str]] = {}
    ungrouped: list[str] = []
    for item in items:
        if item.symbol in index_symbols:
            continue  # 已在内置大盘组中，避免重复出现
        if item.group_id is None:
            ungrouped.append(item.symbol)
        else:
            by_group.setdefault(item.group_id, []).append(item.symbol)

    for group in groups:
        result.append(
            WatchlistGroupDTO(
                group_id=group.group_id,
                name=group.name,
                sort_order=group.sort_order,
                builtin=False,
                symbols=by_group.get(group.group_id, []),
            )
        )
    if ungrouped:
        result.append(
            WatchlistGroupDTO(
                group_id=None,
                name=UNGROUPED_NAME,
                sort_order=9999,
                builtin=True,  # 虚拟组，不可改名/删除
                symbols=ungrouped,
            )
        )
    return result


@router.post("/groups", response_model=WatchlistGroupDTO, status_code=201)
def post_group(request: Request, body: GroupCreateRequest) -> WatchlistGroupDTO:
    if body.name.strip() in (BUILTIN_INDEX_GROUP, UNGROUPED_NAME):
        raise HTTPException(
            status_code=422, detail=f"「{body.name}」是内置分组名，请换一个"
        )
    try:
        with closing(connect(_db_path(request))) as conn:
            group = create_group(conn, body.name)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return WatchlistGroupDTO(
        group_id=group.group_id, name=group.name, sort_order=group.sort_order, symbols=[]
    )


@router.patch("/groups/{group_id}", response_model=WatchlistGroupDTO)
def patch_group(
    request: Request, group_id: int, body: GroupRenameRequest
) -> WatchlistGroupDTO:
    if body.name.strip() in (BUILTIN_INDEX_GROUP, UNGROUPED_NAME):
        raise HTTPException(
            status_code=422, detail=f"「{body.name}」是内置分组名，请换一个"
        )
    try:
        with closing(connect(_db_path(request))) as conn:
            if not rename_group(conn, group_id, body.name):
                raise HTTPException(status_code=404, detail="分组不存在")
            groups = {g.group_id: g for g in list_groups(conn)}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    group = groups[group_id]
    return WatchlistGroupDTO(
        group_id=group.group_id, name=group.name, sort_order=group.sort_order
    )


@router.delete("/groups/{group_id}", status_code=204)
def remove_group(request: Request, group_id: int) -> Response:
    """删组（幂等）。组内标的转为未分组，不会被删除。"""
    with closing(connect(_db_path(request))) as conn:
        delete_group(conn, group_id)
    return Response(status_code=204)
