# LEI 技术体系权威文档索引与 Web 阅读页 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将桌面目录中的两份 LEI 文档登记为项目当前权威源，并提供只读、可按章节导航的 Web 技术体系页面。

**Architecture:** 仓库内只保存固定来源索引和已确认指纹，正文继续留在 `~/Desktop/lei signal doc`。FastAPI 通过固定 ID 读取、验指纹并提取章节；React 页面通过只读接口展示正文和研究范围，不在前端计算任何交易判断。

**Tech Stack:** Python 3.11、FastAPI、pytest、React 18、TypeScript、TanStack Query、marked、DOMPurify、Vite。

## Global Constraints

- 当前策略语义最高来源是 `~/Desktop/lei signal doc/LEI 技术交易体系.md`。
- 当前计算与回测实现来源是 `~/Desktop/lei signal doc/LEI 技术实现.md`。
- 两份桌面文档只读；新增、删除或改变技术含义必须先向用户说明对因子范围的影响并取得确认。
- 仓库不得复制两份正文，也不得在接口中接受任意本地路径。
- `docs/trading-spec-v1.md` 继续作为历史 V1 快照，不能删除、改名或批量改写旧实验引用。
- 宽度、NAAIM 机构情绪和 AAII 散户情绪在新原文与实现 V2.2 中已有；A 股情绪仍标为体系外研究扩展，不能冒充正式规则。
- UI 只修改 `web/`；不得修改冻结的 `src/lei_signal/ui/`。
- 页面只展示，不修改 Python 判定规则、回测参数、生产交易逻辑或桌面源文件。
- 在已有大量未提交改动的工作区中只暂存本任务文件，不使用 `git add .`；修改过的
  既有文件用 `git add -p` 只选择本任务小块，无法安全拆分时保留未提交并在交接说明。

---

### Task 1: 固定来源索引与只读装载器

**Files:**
- Create: `configs/strategy-documents.v1.json`
- Create: `src/lei_signal/api/strategy_documents.py`
- Create: `tests/unit/test_strategy_documents.py`

**Interfaces:**
- Consumes: 仓库索引 `configs/strategy-documents.v1.json` 与 `~/Desktop/lei signal doc/*.md`。
- Produces: `list_documents(repo_root=None, home=None) -> dict`、`read_document(document_id, repo_root=None, home=None) -> dict | None`、`StrategyDocumentError`。

- [ ] **Step 1: 写固定索引**

创建：

```json
{
  "schema_version": "strategy-documents/1",
  "canonical_directory": "~/Desktop/lei signal doc",
  "documents": [
    {
      "id": "technical-system",
      "title": "LEI 技术交易体系",
      "file_name": "LEI 技术交易体系.md",
      "role": "技术思想与交易语义的最高来源",
      "approved_sha256": "df92d85b3b04ed3ab71d56bc108d0effe8eb31051b7a1531eda59edcbf0aab20",
      "confirmed_at": "2026-09-29",
      "order": 1
    },
    {
      "id": "technical-implementation",
      "title": "LEI 技术实现",
      "file_name": "LEI 技术实现.md",
      "role": "当前计算、回测与输出定义的实现依据",
      "approved_sha256": "85e0e3270ff96fe85247756805c58c650a0e83b21ea15c9feccea84d31aaf903",
      "confirmed_at": "2026-09-29",
      "order": 2
    }
  ]
}
```

- [ ] **Step 2: 写装载器失败测试**

测试至少覆盖确认、变化、缺失、重复标题锚点和未知 ID：

```python
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from lei_signal.api import strategy_documents as sd


def _write_fixture(root: Path, home: Path, body: str = "# 总纲\n\n## 道路\n\n## 道路\n") -> str:
    source = home / "Desktop/lei signal doc"
    source.mkdir(parents=True)
    path = source / "LEI 技术交易体系.md"
    path.write_text(body, encoding="utf-8")
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    config = root / "configs"
    config.mkdir(parents=True)
    (config / "strategy-documents.v1.json").write_text(json.dumps({
        "schema_version": "strategy-documents/1",
        "canonical_directory": "~/Desktop/lei signal doc",
        "documents": [{
            "id": "technical-system", "title": "LEI 技术交易体系",
            "file_name": "LEI 技术交易体系.md", "role": "最高来源",
            "approved_sha256": digest, "confirmed_at": "2026-09-29", "order": 1,
        }],
    }, ensure_ascii=False), encoding="utf-8")
    return digest


def test_read_confirmed_document_and_headings(tmp_path: Path) -> None:
    home = tmp_path / "home"
    digest = _write_fixture(tmp_path, home)
    doc = sd.read_document("technical-system", tmp_path, home)
    assert doc is not None
    assert doc["approvalStatus"] == "confirmed"
    assert doc["currentSha256"] == digest
    assert [h["id"] for h in doc["headings"]] == ["总纲", "道路", "道路-2"]


def test_changed_and_missing_are_reported(tmp_path: Path) -> None:
    home = tmp_path / "home"
    _write_fixture(tmp_path, home)
    source = home / "Desktop/lei signal doc/LEI 技术交易体系.md"
    source.write_text("# 已改变\n", encoding="utf-8")
    assert sd.read_document("technical-system", tmp_path, home)["approvalStatus"] == "changed"
    source.unlink()
    summary = sd.list_documents(tmp_path, home)["documents"][0]
    assert summary["approvalStatus"] == "missing"
    with pytest.raises(sd.StrategyDocumentError, match="源文件不存在"):
        sd.read_document("technical-system", tmp_path, home)


def test_unknown_id_and_path_escape(tmp_path: Path) -> None:
    home = tmp_path / "home"
    _write_fixture(tmp_path, home)
    assert sd.read_document("unknown", tmp_path, home) is None
    index = tmp_path / "configs/strategy-documents.v1.json"
    data = json.loads(index.read_text(encoding="utf-8"))
    data["documents"][0]["file_name"] = "../secret.md"
    index.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(sd.StrategyDocumentError, match="权威目录之外"):
        sd.list_documents(tmp_path, home)
```

- [ ] **Step 3: 运行测试，确认失败**

Run: `pytest tests/unit/test_strategy_documents.py -q`  
Expected: FAIL，提示无法导入 `lei_signal.api.strategy_documents`。

- [ ] **Step 4: 实现固定索引、指纹和标题解析**

实现要点如下；字段名必须与测试及前端类型一致：

```python
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path

_INDEX = Path("configs/strategy-documents.v1.json")
_HEADING = re.compile(r"^(#{1,3})\s+(.+?)\s*$")


class StrategyDocumentError(RuntimeError):
    pass


def _repo_root(base: Path | None = None) -> Path:
    return base or Path(__file__).resolve().parents[3]


def _slug(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).strip().lower()
    normalized = re.sub(r"[`*_~]", "", normalized)
    return re.sub(r"[^\w\u4e00-\u9fff-]+", "-", normalized).strip("-") or "section"


def _headings(markdown: str) -> list[dict]:
    counts: dict[str, int] = {}
    result = []
    for line in markdown.splitlines():
        match = _HEADING.match(line)
        if not match:
            continue
        text = match.group(2).strip().rstrip("#").strip()
        base = _slug(text)
        counts[base] = counts.get(base, 0) + 1
        anchor = base if counts[base] == 1 else f"{base}-{counts[base]}"
        result.append({"id": anchor, "text": text, "level": len(match.group(1))})
    return result


def _load_index(repo_root: Path) -> dict:
    path = repo_root / _INDEX
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise StrategyDocumentError(f"策略文档索引不可用：{path}") from exc
    if data.get("schema_version") != "strategy-documents/1":
        raise StrategyDocumentError("策略文档索引版本不受支持")
    return data


def _resolve_sources(repo_root: Path, home: Path) -> list[tuple[dict, Path]]:
    index = _load_index(repo_root)
    raw_dir = str(index["canonical_directory"])
    canonical = (home / raw_dir[2:]).resolve() if raw_dir.startswith("~/") else Path(raw_dir).resolve()
    rows = []
    for entry in sorted(index["documents"], key=lambda item: item["order"]):
        source = (canonical / entry["file_name"]).resolve()
        if source.parent != canonical:
            raise StrategyDocumentError("策略文档路径落在权威目录之外")
        rows.append((entry, source))
    return rows


def _summary(entry: dict, source: Path) -> dict:
    if not source.is_file():
        return {**entry, "path": str(source), "available": False,
                "currentSha256": None, "approvalStatus": "missing", "modifiedAt": None}
    payload = source.read_bytes()
    current = hashlib.sha256(payload).hexdigest()
    modified = datetime.fromtimestamp(source.stat().st_mtime).astimezone().isoformat()
    return {**entry, "path": str(source), "available": True,
            "currentSha256": current,
            "approvalStatus": "confirmed" if current == entry["approved_sha256"] else "changed",
            "modifiedAt": modified}


def list_documents(repo_root: Path | None = None, home: Path | None = None) -> dict:
    rows = [_summary(entry, path) for entry, path in
            _resolve_sources(_repo_root(repo_root), home or Path.home())]
    return {"documents": rows}


def read_document(document_id: str, repo_root: Path | None = None,
                  home: Path | None = None) -> dict | None:
    for entry, source in _resolve_sources(_repo_root(repo_root), home or Path.home()):
        if entry["id"] != document_id:
            continue
        summary = _summary(entry, source)
        if not summary["available"]:
            raise StrategyDocumentError(f"策略源文件不存在：{source}")
        try:
            markdown = source.read_text(encoding="utf-8")
        except UnicodeError as exc:
            raise StrategyDocumentError(f"策略源文件不是有效 UTF-8：{source}") from exc
        return {**summary, "markdown": markdown, "headings": _headings(markdown)}
    return None
```

- [ ] **Step 5: 运行装载器测试**

Run: `pytest tests/unit/test_strategy_documents.py -q`  
Expected: `3 passed`。

- [ ] **Step 6: 只提交本任务文件**

```bash
git add configs/strategy-documents.v1.json src/lei_signal/api/strategy_documents.py tests/unit/test_strategy_documents.py
git commit -m "feat: index canonical LEI strategy documents"
```

---

### Task 2: 只读 API 路由

**Files:**
- Create: `src/lei_signal/api/routes/strategy_documents.py`
- Modify: `src/lei_signal/api/app.py:23-47,141-165`
- Modify: `tests/unit/test_strategy_documents.py`

**Interfaces:**
- Consumes: Task 1 的 `list_documents`、`read_document` 和异常类型。
- Produces: `GET /api/strategy-documents` 与 `GET /api/strategy-documents/{document_id}`。

- [ ] **Step 1: 添加 API 失败测试**

```python
from fastapi.testclient import TestClient

from lei_signal.api.app import create_app


def test_strategy_document_routes(monkeypatch, tmp_path: Path) -> None:
    home = tmp_path / "home"
    _write_fixture(tmp_path, home)
    monkeypatch.setattr(sd, "_repo_root", lambda base=None: tmp_path)
    monkeypatch.setattr(sd.Path, "home", lambda: home)
    client = TestClient(create_app())
    listed = client.get("/api/strategy-documents")
    assert listed.status_code == 200
    assert listed.json()["documents"][0]["id"] == "technical-system"
    detail = client.get("/api/strategy-documents/technical-system")
    assert detail.status_code == 200
    assert detail.json()["headings"][1]["text"] == "道路"
    assert client.get("/api/strategy-documents/unknown").status_code == 404
    assert client.get("/api/strategy-documents/../AGENTS.md").status_code in (404, 422)
```

- [ ] **Step 2: 运行单测，确认路由失败**

Run: `pytest tests/unit/test_strategy_documents.py::test_strategy_document_routes -q`  
Expected: FAIL，`/api/strategy-documents` 尚未注册。

- [ ] **Step 3: 创建路由并注册**

```python
from fastapi import APIRouter, HTTPException

from lei_signal.api import strategy_documents as sd

router = APIRouter(prefix="/api/strategy-documents", tags=["strategy-documents"])


@router.get("")
def list_strategy_documents() -> dict:
    try:
        return sd.list_documents()
    except sd.StrategyDocumentError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/{document_id}")
def get_strategy_document(document_id: str) -> dict:
    try:
        document = sd.read_document(document_id)
    except sd.StrategyDocumentError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if document is None:
        raise HTTPException(status_code=404, detail="未登记的策略文档")
    return document
```

在 `app.py` 的路由导入表中加入 `strategy_documents`，并在 `learning` 附近执行：

```python
app.include_router(strategy_documents.router)
```

- [ ] **Step 4: 运行 API 测试与静态检查**

Run: `pytest tests/unit/test_strategy_documents.py -q`  
Expected: 全部 PASS。  
Run: `ruff check src/lei_signal/api/strategy_documents.py src/lei_signal/api/routes/strategy_documents.py tests/unit/test_strategy_documents.py`  
Expected: `All checks passed!`。

- [ ] **Step 5: 提交 API**

```bash
git add src/lei_signal/api/routes/strategy_documents.py
git add -p src/lei_signal/api/app.py tests/unit/test_strategy_documents.py
git diff --cached --name-only
git commit -m "feat: expose read-only strategy document API"
```

---

### Task 3: 替换新任务的权威指针

**Files:**
- Modify: `AGENTS.md`
- Modify: `docs/README.md`
- Modify: `docs/system-architecture-and-decisions-2026-09-04.md`
- Modify: `docs/research/experiment-backtest-principles.md`
- Modify: `docs/research/definition-standard.md`
- Modify: `docs/research/factor-admission/README.md`
- Modify: `docs/research/lei-factor-research-mission.md`
- Modify: `web/DESIGN.md`
- Modify: `web/AGENT-WORKSPACE.md`

**Interfaces:**
- Consumes: Task 1 的固定路径、角色和指纹规则。
- Produces: 新任务统一读取两份桌面文档，历史材料仍保留 V1 引用。

- [ ] **Step 1: 先列出当前指针，不碰历史材料**

Run:

```bash
rg -n --glob '!docs/experiments/**' --glob '!docs/archive/**' --glob '!docs/superpowers/**' \
  'trading-spec-v1|最高溯源依据' AGENTS.md docs/research docs/README.md \
  docs/system-architecture-and-decisions-2026-09-04.md web/DESIGN.md web/AGENT-WORKSPACE.md
```

Expected: 输出仅作为逐项修改清单；不要对 `definitions.v1.json`、冻结协议、历史计划或实验报告执行全局替换。

- [ ] **Step 2: 更新根约束的第零步**

将 `AGENTS.md` 现有“第零步”首项替换为以下职责表述，并保留规则账本、MACD 与板块方案条目：

```markdown
- `~/Desktop/lei signal doc/LEI 技术交易体系.md` — 技术思想与交易语义的最高来源。
- `~/Desktop/lei signal doc/LEI 技术实现.md` — 当前计算、回测与输出定义的实现依据。
- `configs/strategy-documents.v1.json` — 两份权威源的固定路径和用户已确认指纹；
  指纹变化时只可阅读和报告差异，不得据此扩大或缩小因子研究范围。
- `docs/trading-spec-v1.md` — 历史 V1 快照，只用于复现旧实验，不再定义新任务。
```

紧接着新增不可变更条款：

```markdown
任何 agent 不得直接新增、删除或改写两份桌面文档中的技术内容。需要改变道路、
路牌、触发、失效、退出、过滤、输入变量或研究范围时，必须先向用户列出变化、
受影响的因子对象及历史实验可比性，取得确认后再更新原文和确认指纹。
```

- [ ] **Step 3: 更新当前研究入口**

在其余文件中使用同一职责语句，确保表达以下事实：

```markdown
新研究先读《LEI 技术交易体系》和《LEI 技术实现》；`docs/trading-spec-v1.md`
只在复现冻结 V1 实验时使用。研究规范管理“如何检验”，不改写两份权威源。
```

`factor-admission/README.md` 的挂靠规则改成：候选先挂到新技术体系或新实现的具体章节；挂不上时只能作为“体系外研究扩展”，不能冒充正式 LEI 因子。

- [ ] **Step 4: 复核旧材料没有被误改**

Run:

```bash
git diff -- AGENTS.md docs/README.md docs/system-architecture-and-decisions-2026-09-04.md \
  docs/research/experiment-backtest-principles.md docs/research/definition-standard.md \
  docs/research/factor-admission/README.md docs/research/lei-factor-research-mission.md \
  web/DESIGN.md web/AGENT-WORKSPACE.md
```

Expected: 只有当前导航与规范入口变化；没有改动 `docs/experiments/`、`docs/archive/`、`definitions.v1.json` 或桌面源文档。

- [ ] **Step 5: 提交权威指针更新**

只暂存这些文件中的本任务小块；若文件在任务前已经有别的改动，看到无关小块时输入
`n`，混合小块先输入 `s` 拆分：

```bash
git add -p AGENTS.md docs/README.md docs/system-architecture-and-decisions-2026-09-04.md \
  docs/research/experiment-backtest-principles.md docs/research/definition-standard.md \
  docs/research/factor-admission/README.md docs/research/lei-factor-research-mission.md \
  web/DESIGN.md web/AGENT-WORKSPACE.md
git diff --cached --name-only
git commit -m "docs: point current research to canonical LEI sources"
```

---

### Task 4: 前端数据合同与安全 Markdown 渲染

**Files:**
- Modify: `web/package.json`
- Modify: `web/package-lock.json`
- Modify: `web/src/types.ts`
- Modify: `web/src/api/client.ts`
- Create: `web/src/pages/strategySystemLogic.ts`
- Create: `web/run-strategy-system-regression.mjs`

**Interfaces:**
- Consumes: Task 2 的两个只读 API。
- Produces: `strategyDocumentsApi`、策略文档 TypeScript 类型、`RESEARCH_EXTENSIONS` 和 `normalizeSelectedDocumentId`。

- [ ] **Step 1: 安装受控 HTML 清理库**

Run: `cd web && npm install dompurify@^3.2.6`  
Expected: `package.json` 与 `package-lock.json` 同步更新；不得删除或升级无关依赖。

- [ ] **Step 2: 添加前端数据类型**

在 `web/src/types.ts` 的实验报告类型附近添加：

```ts
export type StrategyDocumentApprovalStatus = "confirmed" | "changed" | "missing";

export interface StrategyDocumentHeading {
  id: string;
  text: string;
  level: 1 | 2 | 3;
}

export interface StrategyDocumentSummary {
  id: string;
  title: string;
  file_name: string;
  role: string;
  approved_sha256: string;
  confirmed_at: string;
  order: number;
  path: string;
  available: boolean;
  currentSha256: string | null;
  approvalStatus: StrategyDocumentApprovalStatus;
  modifiedAt: string | null;
}

export interface StrategyDocumentsResponse {
  documents: StrategyDocumentSummary[];
}

export interface StrategyDocumentDetail extends StrategyDocumentSummary {
  markdown: string;
  headings: StrategyDocumentHeading[];
}
```

- [ ] **Step 3: 增加 API 客户端**

把新类型加入 `client.ts` 顶部的类型导入，并添加：

```ts
export const strategyDocumentsApi = {
  list: () => request<StrategyDocumentsResponse>("/strategy-documents"),
  detail: (documentId: string) =>
    request<StrategyDocumentDetail>(`/strategy-documents/${encodeURIComponent(documentId)}`),
};
```

- [ ] **Step 4: 写研究范围和选择逻辑**

```ts
export type ResearchExtension = {
  id: string;
  name: string;
  plainDefinition: string;
  sourceClass: "原文与实现已有" | "体系外研究扩展";
  status: string;
  to: string;
};

export const RESEARCH_EXTENSIONS: ResearchExtension[] = [
  {
    id: "breadth", name: "市场宽度",
    plainDefinition: "一篮子成分里，有多少标的站上各自均线，用来判断上涨或下跌参与面。",
    sourceClass: "原文与实现已有", status: "模块 E 已定义，具体市场仍需独立检验", to: "/sectors",
  },
  {
    id: "institutional", name: "机构情绪",
    plainDefinition: "用 NAAIM 等资料观察机构风险敞口是否走到人性极端。",
    sourceClass: "原文与实现已有", status: "模块 E 已定义，数据资格和增量仍需检验", to: "/sentiment",
  },
  {
    id: "retail", name: "散户情绪",
    plainDefinition: "用 AAII 等调查观察散户看多和看空是否走到极端。",
    sourceClass: "原文与实现已有", status: "模块 E 已定义，数据资格和增量仍需检验", to: "/sentiment",
  },
  {
    id: "a-share-sentiment", name: "A 股情绪",
    plainDefinition: "研究适合 A 股市场的成交、涨跌分布和投资者行为信息。",
    sourceClass: "体系外研究扩展", status: "待逐项定义和检验，未经确认不进入正式策略", to: "/factors",
  },
];

export function normalizeSelectedDocumentId(requested: string | null, ids: string[]): string | null {
  if (requested && ids.includes(requested)) return requested;
  return ids[0] ?? null;
}
```

- [ ] **Step 5: 添加轻量回归脚本**

脚本先读取并检查真实源文件，再验证选择逻辑和四个研究入口。`package.json` 新增：

```json
"test:strategy-system": "esbuild src/pages/strategySystemLogic.ts --bundle --platform=node --format=esm --outfile=/tmp/lei-strategy-system-logic.mjs && node run-strategy-system-regression.mjs"
```

`run-strategy-system-regression.mjs` 需断言：非法 `doc` 回落第一项、空列表返回 `null`、四项范围齐全、A 股情绪为“体系外研究扩展”、宽度/机构/散户为“原文与实现已有”。

- [ ] **Step 6: 运行前端逻辑测试和构建**

Run: `cd web && npm run test:strategy-system`  
Expected: 输出 `strategy-system regression passed`。  
Run: `cd web && npm run build`  
Expected: TypeScript 与 Vite build PASS。

- [ ] **Step 7: 提交数据合同**

```bash
git add web/src/pages/strategySystemLogic.ts web/run-strategy-system-regression.mjs
git add -p web/package.json web/package-lock.json web/src/types.ts web/src/api/client.ts
git diff --cached --name-only
git commit -m "feat: add strategy document web contracts"
```

---

### Task 5: 技术体系阅读页、章节导航与入口

**Files:**
- Create: `web/src/pages/StrategySystemPage.tsx`
- Create: `web/src/pages/strategy-system.css`
- Modify: `web/src/App.tsx:1-25,70-105`
- Modify: `web/src/components/TopNav.tsx:47-75`
- Modify: `web/run-strategy-system-regression.mjs`

**Interfaces:**
- Consumes: Task 4 的 API、类型、选择逻辑、研究扩展表，以及 DOMPurify。
- Produces: `/strategy` 页面和“策略研究 → 技术体系”导航入口。

- [ ] **Step 1: 先给回归脚本加入源文件守卫**

断言以下真实代码标记必须存在：

```js
assert.ok(page.includes("DOMPurify.sanitize"), "正文必须清理危险 HTML");
assert.ok(page.includes("IntersectionObserver"), "章节目录必须跟随阅读位置");
assert.ok(page.includes("approvalStatus === \"changed\""), "必须提示未经确认的源文件变化");
assert.ok(app.includes('path="/strategy"'), "App 必须注册 /strategy");
assert.ok(nav.includes('{ to: "/strategy", label: "技术体系" }'), "顶栏必须提供技术体系入口");
```

Run: `cd web && npm run test:strategy-system`  
Expected: FAIL，因为页面和路由尚未创建。

- [ ] **Step 2: 建立页面数据流**

页面使用两个查询：

```tsx
const listQuery = useQuery({
  queryKey: ["strategy-documents"],
  queryFn: strategyDocumentsApi.list,
  staleTime: 60_000,
});
const ids = listQuery.data?.documents.map((item) => item.id) ?? [];
const selectedId = normalizeSelectedDocumentId(searchParams.get("doc"), ids);
const detailQuery = useQuery({
  queryKey: ["strategy-document", selectedId],
  queryFn: () => strategyDocumentsApi.detail(selectedId!),
  enabled: selectedId != null,
  staleTime: 60_000,
});
const html = useMemo(() => {
  if (!detailQuery.data) return "";
  return DOMPurify.sanitize(marked.parse(detailQuery.data.markdown, { async: false }) as string);
}, [detailQuery.data]);
```

在查询成功后，如果 URL 没有合法 `doc`，用 `setSearchParams({doc: selectedId}, {replace: true})` 写回；切换文档时删除旧 `section`。

- [ ] **Step 3: 实现稳定章节锚点和阅读位置高亮**

正文渲染后按 API 返回顺序给 `articleRef.current.querySelectorAll("h1,h2,h3")` 设置 `id`。建立 `IntersectionObserver`：

```tsx
const observer = new IntersectionObserver(
  (entries) => {
    const visible = entries.filter((entry) => entry.isIntersecting)
      .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)[0];
    if (visible?.target.id) setActiveHeading(visible.target.id);
  },
  { rootMargin: "-96px 0px -70% 0px", threshold: [0, 1] },
);
```

目录点击时保留 `doc`、写入 `section`，并对目标调用 `scrollIntoView({behavior: prefersReducedMotion ? "auto" : "smooth"})`。首次加载有合法 `section` 时，在标题 ID 设置完成后滚动到目标。

- [ ] **Step 4: 完成页面结构和状态提示**

页面至少包含以下语义节点：

```tsx
<main className="strategy-page">
  <header className="strategy-header">…两份文档切换、角色、更新时间…</header>
  {detail.approvalStatus === "changed" && (
    <div className="strategy-source-alert" role="alert">
      源文件已变化，尚未确认。当前内容可以阅读，但不能据此扩大或缩小因子研究范围。
    </div>
  )}
  <div className="strategy-reader-layout">
    <nav className="strategy-toc" aria-label="本文章节">…</nav>
    <article ref={articleRef} className="strategy-markdown"
      dangerouslySetInnerHTML={{ __html: html }} />
  </div>
  <section className="strategy-extensions" aria-labelledby="strategy-extensions-title">…四项研究范围…</section>
</main>
```

确认状态文案：`confirmed` 显示“已确认来源”；`changed` 显示上述警告；`missing` 在文档切换处显示“源文件缺失”。加载失败显示接口返回的具体中文信息和登记路径，不回退旧 V1。

- [ ] **Step 5: 完成页面视觉与窄屏行为**

`strategy-system.css` 使用现有 CSS 变量；要求：

- 阅读列最大宽度约 `780px`，正文行高 `1.75`；
- 左侧目录宽 `250px`、`position: sticky`、顶距适配现有顶栏；
- 一级到三级目录按真实层级缩进，不添加无意义编号；
- 表格横向滚动，代码块不撑破页面；
- `changed` 警告使用高对比边框与文字，不以颜色作为唯一提示；
- `@media (max-width: 760px)` 时目录改为原生 `<details>` 折叠区，正文单列；
- `:focus-visible` 清楚，`prefers-reduced-motion` 下关闭平滑滚动和动画。

- [ ] **Step 6: 注册路由和导航**

`App.tsx` 导入 `StrategySystemPage` 并加入：

```tsx
<Route path="/strategy" element={<StrategySystemPage />} />
```

`TopNav.tsx` 的“策略研究”组首项加入：

```ts
{ to: "/strategy", label: "技术体系" },
```

- [ ] **Step 7: 运行回归和构建**

Run: `cd web && npm run test:strategy-system`  
Expected: PASS。  
Run: `cd web && npm run build`  
Expected: PASS，且无 TypeScript 错误。

- [ ] **Step 8: 提交页面**

```bash
git add web/src/pages/StrategySystemPage.tsx web/src/pages/strategy-system.css \
  web/run-strategy-system-regression.mjs
git add -p web/src/App.tsx web/src/components/TopNav.tsx
git diff --cached --name-only
git commit -m "feat: add LEI strategy system reader"
```

---

### Task 6: 集成验证与页面检查

**Files:**
- Modify only if a test reveals a defect in Task 1–5 files.

**Interfaces:**
- Consumes: 全部前述任务。
- Produces: 可交付的 API、页面、规范指针和验证证据。

- [ ] **Step 1: 验证真实源文件和确认指纹**

Run:

```bash
shasum -a 256 "$HOME/Desktop/lei signal doc/LEI 技术交易体系.md" \
  "$HOME/Desktop/lei signal doc/LEI 技术实现.md"
```

Expected: 分别为
`df92d85b3b04ed3ab71d56bc108d0effe8eb31051b7a1531eda59edcbf0aab20` 与
`85e0e3270ff96fe85247756805c58c650a0e83b21ea15c9feccea84d31aaf903`。如果不一致，
停止更新确认指纹，报告差异并等待用户确认；不要修改源文件。

- [ ] **Step 2: 运行后端目标测试和静态检查**

Run: `pytest tests/unit/test_strategy_documents.py -q`  
Expected: PASS。  
Run: `ruff check src/lei_signal/api/strategy_documents.py src/lei_signal/api/routes/strategy_documents.py tests/unit/test_strategy_documents.py`  
Expected: PASS。

- [ ] **Step 3: 运行前端测试和构建**

Run: `cd web && npm run test:strategy-system && npm run build`  
Expected: 两项 PASS。

- [ ] **Step 4: 启动本地服务并检查页面**

使用项目既有启动方式，不新建脚本。检查：

1. 1440px 宽度下两份文档切换、目录定位、表格和长段落；
2. 390px 宽度下目录折叠、文档切换、正文不横向溢出；
3. `/strategy?doc=technical-system&section=第三部分-预警系统-什么情况要瞪大眼睛` 可恢复位置；
4. 宽度、NAAIM、AAII 标成“原文与实现已有”；A 股情绪标成“体系外研究扩展”；
5. 临时用测试夹具验证 `changed` 和缺失状态后恢复，不改真实桌面文档。

- [ ] **Step 5: 检查本任务差异和目录规范**

Run: `python3 scripts/check_repo_hygiene.py`  
Expected: PASS；若失败，只修本任务新引入的问题，不清理用户已有文件。  
Run: `git diff --check`  
Expected: 无空白错误。  
Run:

```bash
git status --short
git diff --name-only HEAD~5..HEAD
```

Expected: 本任务没有修改 `src/lei_signal/ui/`、桌面源文档、历史实验或冻结材料。

- [ ] **Step 6: 最终交接**

交接只需报告：页面入口、两份权威源的确认状态、更新过的当前规范入口、测试结果、任何仍存在的限制。不要把“页面可读”写成“策略已经验证有效”，也不要宣布 A 股情绪已进入正式体系。
