"""文献学习库 · 路由。

前缀 ``/api/learning``。只读：数据全部来自仓库内
``docs/literature-learning/learning-seed.json`` 固定内容文件，本路由
不产生、不修改任何学习内容，无写接口，不接受任意本地路径参数。
学习内容是学习与研究说明层，不参与道路、路牌、技术入场或过滤判定。
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from lei_signal.api import learning_library as ll

router = APIRouter(prefix="/api/learning", tags=["learning"])


@router.get("")
def get_learning_library() -> dict:
    """学习目录全量（论文 + 条目 + 学习路线 + 统计）。

    第一版单接口：内容总量小（首期 18 篇 / 20 条），筛选与展示全部在
    前端做。内容文件缺失或非法 → 503，前端显示「学习资料暂不可用」。
    """
    try:
        return ll.load_library()
    except ll.LearningDataError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
