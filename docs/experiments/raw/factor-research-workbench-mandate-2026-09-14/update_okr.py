"""本轮主控限定的OKR登记；只运行一次，不标完成。"""
import json
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

BASE = "http://127.0.0.1:8000/api/upgrades"
HERE = Path(__file__).resolve().parent
REPORT = "docs/experiments/factor-research-workbench-mandate-2026-09-14.md"
LINK = {"label": "自有因子体系目标与首轮执行计划", "url": "/library?report=" + quote(REPORT, safe="")}


def call(method, suffix="", payload=None):
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode()
    req = Request(BASE + suffix, data=data, method=method,
                  headers={"Content-Type": "application/json"})
    with urlopen(req, timeout=15) as response:
        return json.load(response)


def save(name, data):
    with (HERE / name).open("x", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    goals = call("GET")["items"]
    direction_title = "建设LeiSignal自有因子与信号研究体系"
    task_title = "首轮：通用因子计算、检验与策略归因工具"
    if any(g["title"] in {direction_title, task_title} for g in goals):
        raise RuntimeError("目标已存在，停止重复创建，交主控核对")
    old = next(g for g in goals if g["id"] == "okr-4f4157e2957e")
    save("okr-before.json", {"existing_titles": [{"id": g["id"], "title": g["title"]} for g in goals], "external_goal": old})
    direction = call("POST", payload={
        "kind": "directional", "title": direction_title, "priority": "high",
        "owner": "用户与Codex主控；ZCode按具体任务执行",
        "purpose": "建立可追溯的自有因子与信号库，支持双均线、宽度等技术对象的定义/计算、预测与状态检验、试验史和过拟合风险、策略三层归因、适用标的与实际执行验收。固定池是每次实验的约束，不是库的边界；最终服务真实交易依据，但研究不自动授予交易权限。",
        "next_action": "先执行首轮离线通用研究工具任务；资料不足只限制对应真实结论，不再以补齐14只ETF资料作为通用建设总前置条件。后续因子开发与真实检验逐项冻结授权。",
        "evidence": "2026-09-14用户明确希望自己的因子库、双均线/宽度、IC、过拟合风险、策略归因和适用标的，并授权更新OKR及通过ZCode派发。当前只完成方向与计划，不宣称能力已交付或因子有效。",
        "links": [LINK], "milestones": []})
    save("okr-direction-created.json", direction)
    task = call("POST", payload={
        "kind": "concrete", "title": task_title, "parent_id": direction["id"],
        "priority": "high", "owner": "ZCode执行；Codex独立复核",
        "purpose": "按2026-09-14-factor-research-workbench-v1.md v1.0.0实现研究专用通用接口，不改既有引擎/卡/生产。复用已有计算，3类合成例验证数值、状态检验、过拟合风险和资金/决策归因，风险模型缺条件明确不运行。",
        "next_action": "准备新ZCode空任务并核workspace/job身份后发送；回调后主控独立复核，更新证据和进度，不由执行者自行验收。",
        "evidence": "仅计划与当前代码复用面核对完成；源代码实现、测试与正式合成运行尚未开始。",
        "milestones": [
            {"id": "interfaces", "title": "统一引用/输入/元数据和不同合成实体集合可调用；既有对象/双均线候选/宽度边界明确", "done": False},
            {"id": "diagnostics", "title": "预测IC与状态诊断分流，未来标签/缺值/并列/共同状态处理经独立小例核验", "done": False},
            {"id": "validation", "title": "尝试史、时间切分、标签重叠及已看过验证资料可追溯，不伪称排除过拟合", "done": False},
            {"id": "attribution", "title": "资金贡献对账、受控决策比较及风险模型资格入口真实调用，未实现项明确", "done": False},
            {"id": "delivery", "title": "三类合成端到端产物、测试/保护证据、使用文档齐备并交主控复核", "done": False}],
        "links": [LINK]})
    save("okr-task-created.json", task)
    scope = ("用户2026-09-14授权：更新相关OKR并通过ZCode发送长执行任务。"
             "仅执行docs/superpowers/plans/2026-09-14-factor-research-workbench-v1.md v1.0.0："
             "新factor_lab研究包/CLI/测试/手册/报告，零新行情/依赖/真实收益或账户运行；"
             "真实只读资格最多1批，合成正式3类各初跑1+纠错1，完整相关回归最多2次。"
             "不改生产/旧卡/旧引擎/旧封存，不交易不提交git；执行者不写OKR，主控按证据同步且不提前完成。")
    task = call("POST", f"/{task['id']}/actions", {"version": task["version"], "action": "authorize", "note": "登记本次用户明确授权，非默认授予整个方向。", "scope": scope})
    save("okr-task-authorized.json", task)
    old = call("PATCH", f"/{old['id']}", {"version": old["version"], "parent_id": direction["id"],
        "next_action": "2026-09-14：作为自有因子体系的后续外部资源专项保留。当前先执行通用研究能力首轮；不以本条资料补齐为总前置，外部库/数据采用仍按具体需求另授权。",
        "links": old["links"] + [LINK, {"label": "自有因子与信号研究方向", "url": "/upgrades?goal=" + direction["id"]}]})
    old = call("POST", f"/{old['id']}/actions", {"version": old["version"], "action": "note", "note": "用户明确主目标是自有因子体系；本条外部资源任务保留历史和4项未完成标准，仅关联新方向并后置，不新增外部执行授权。", "scope": "仅目标关联和下一步；完成度不变"})
    save("okr-external-updated.json", old)
    summary = {"direction_id": direction["id"], "direction_version": direction["version"],
               "task_id": task["id"], "task_version": task["version"], "task_status": task["status"],
               "external_id": old["id"], "external_version": old["version"],
               "new_milestones_completed": 0}
    save("okr-summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
