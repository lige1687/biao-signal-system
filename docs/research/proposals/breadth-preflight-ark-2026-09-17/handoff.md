# 执行交接（S1 → 主控）

job `a45965db-162c-4ab6-bbba-e836318d9ee8`，stage=S1，attempt=initial，
2026-09-18，执行者 ZCode GLM-5.3-Flash/high。分支 `codex/factor-unit-research-20260915`，
HEAD `7f8c38c36981b2d176381181bc6a8bb901df618c`（开工/收工一致）。

## 执行者声明

- 按冻结任务书 `docs/archive/handoffs-plans/2026-09-17-breadth-preflight-ark.md`
  全部工作项完成 S1；执行者由 Ark 改为本会话（用户 2026-09-18 指定），任务
  内容未改。
- 预算：独立合成检查命令 1/4（一次通过，无重跑）；完整 CLI 0/0；ruff 新
  检查文件 1/1；hygiene 1/1。逐次记录在 `checks.log`。
- 保护核对：`src/`、`tests/`、旧 raw、协议/规范/registry/INDEX/OKR 零写入
  （收工 `git status` 复核，本轮新增文件全部在交付目录内）；零联网、零安装、
  零真实统计；未提交、未切分支、未派子 agent。
- 未执行自己建议的下一阶段（v1.0.1 修复与任何真实运行均未启动）。

## 证据（均为一手，未转述执行者以外来源）

- G1：`source-manifest.json`——四输入、五规范哈希与合同白名单逐一命中；
  冻结代码副本与现库逐字节一致；run-01 仅 `rejection.json`（docs/docs 路径
  报错）；冻结协议身份常量与合同模块逐项一致。
- G2：`review.md` §2 合同对照 22 条（文件行号）+ §3 合成反例 28 项全过
  （`checks/run-01-pytest.log`），期望值全部手算固定、来源为合同而非实现。
- 缺陷：F1 = `run_breadth.py:31-32` `parents[3]` 少一层（独立确认，未修）；
  F2 低危（宽度非交易日拒绝仅限评价窗、价格全局，不对称）；F3/F4/F5 记录性。
- 独立核验脚本 `verify_result.py` 独立性成立（review §5，含其 3 项缺口）。

## 待主控决定

1. 是否批准按 review §7 规格做 v1.0.1 最小返修（R1 路径行 + 版本/路径常量
   重冻结 + R2 路径回归护栏；F2/F3/F5 是否顺手收紧由主控裁定）。
2. 是否给一次（且仅一次）补救真实运行授权——本报告不批准、不预支。
3. F2 的口径（窗外非交易日宽度行静默忽略）接受为现状还是随 v1.0.1 收紧。

## 限制

未读真实输入数据内容（只算哈希）；未复跑既有 47 项测试与旧回归；未运行
任何完整 CLI；冻结旧模块内部逻辑只查哈希与顶层副作用。以上均为任务书约束
内的未核项，如实不记通过。

---

# 返修轮附录（execution=2, attempt=repair, 2026-09-18）

按主控复核 `docs/experiments/breadth-preflight-controller-review-2026-09-18.md`
（R1/R2/R3）在原会话、原目录内补件；execution=1 报告与检查文件原字节已封存
（`checks/archive-pre-repair-2026-09-18/`，含 SHA）。

## 执行者声明（返修轮）

- 只补协议身份与核验器合成反例，收窄结论；被审实现、冻结协议、旧 raw、
  registry/INDEX/OKR 零改动；零完整 CLI、零真实统计、零联网安装。
- 预算：新增合成检查 2/3（首跑 15 过/5 败为检查文件自身夹具笔误
  `mkdir` 缺 `parents=True`，修后重跑 20/20）；ruff 追加 1/1 已消耗
  （1 处 F401 失败，删该导入后按预算不再复验，如实记录于 checks.log）；
  hygiene 追加 1/1 通过。

## 证据（返修轮新增）

- **R1 协议身份**（`checks/test_protocol_identity_checks.py`，14 项）：合法
  合成协议正例零错误；删 object/family/规范条目、改对象引用、改用途、改
  规范哈希、缺 fixtures 声明、代码键非 SHA、mode 不一致、指针冒充原件各自
  **到达预期校验分支并报出预期错误文本**；`verify_code_manifest` 双向三支路
  （missing key / hash mismatch+drifted / declared missing）逐一验证。
- **R2 核验器**（`checks/test_verifier_independent_checks.py`，6 项）：手造
  合成 run（期望手算固定：rho=-1、8 干净行+22 缺目标行、重叠 168/28/20），
  直调 `verify_run`——清洁组通过且到达键集核对（30=30）；删行、额外行、NaN、
  单位错、目标错五种破坏逐一被抓并断言具体错误文本。未发现漏抓，无新增
  实质问题，未改被审实现。
- **R3 收窄**：review.md 一句话结论/§3/§8 改为按实际覆盖范围表述；明确
  名次相关 0 ≠「没有关系」、AST 检查为 import 后有限静态检查；缺陷清单
  在 F2–F5 裁定前不闭合。

## 待主控决定（不变，新增一项）

1. 是否批准按 review §7 规格做 v1.0.1 最小返修（R1 路径行 + 版本/路径常量
   重冻结 + R2 路径回归护栏；F2/F3/F5 是否顺手收紧由主控裁定）。
2. 是否给一次（且仅一次）补救真实运行授权——本报告不批准、不预支。
3. F2 的口径（窗外非交易日宽度行静默忽略）接受为现状还是随 v1.0.1 收紧。
4. ruff 追加额度已耗尽且含一次失败（F401 已修复但未复验）——如需 lint
   全绿结论，请主控在其自身核查中补验或授权一次复跑。
