# Local Cross-Agent Delegation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local, token-free-between-checkpoints runner that lets Codex dispatch one bounded task to Claude Code or ZCode, inspect progress in a terminal dashboard, stop it safely, and review evidence after completion.

**Architecture:** A small standalone Python package under `tools/agent_delegate/` owns task validation, isolated workspace snapshots, provider commands, one foreground provider process per detached runner, state files, event capture, stopping, and completion checks. `scripts/agent_delegate.py` is the user-facing CLI; a project Skill tells Codex how to call it without widening permissions.

**Tech Stack:** Python 3.11 standard library (`argparse`, `dataclasses`, `fcntl`, `hashlib`, `json`, `os`, `pathlib`, `queue`, `shutil`, `signal`, `subprocess`, `threading`, `time`), pytest, Claude Code 2.1.258, ZCode CLI 0.16.3.

## Global Constraints

- This is developer tooling only: do not modify `web/`, `src/lei_signal/ui/`, trading rules, market data code, production databases, or strategy behavior.
- Default to `review`; the first real CC and ZCode checks run only against temporary repositories.
- Never use `bypassPermissions`, `dangerously-skip-permissions`, ZCode `yolo`, shell command strings, automatic retries, automatic resumes, automatic patch application, or automatic commits.
- Providers work only in a task-owned copied workspace. The source workspace is never a provider `cwd`.
- One active task per canonical source workspace. A busy workspace returns `workspace_busy`; there is no queue.
- `completed` means provider exit 0, non-empty parsed result, no scope violation, required verification passed, cleanup confirmed, and result files durably written. It never means Codex-reviewed or merge-approved.
- State lives outside the repository at `~/.local/state/agent-delegate/`; tests inject a temporary state root.
- The dashboard reads files only and never invokes a model.
- Execute this plan inline in the current task because the user did not request subagents.

---

### Task 1: Task model, safe paths, redaction, and isolated snapshots

**Files:**
- Create: `tools/__init__.py`
- Create: `tools/agent_delegate/__init__.py`
- Create: `tools/agent_delegate/core.py`
- Test: `tests/unit/test_agent_delegate_core.py`

**Interfaces:**
- Produces: `TaskRequest`, `TaskPaths`, `ValidationError`, `default_state_root()`, `task_paths()`, `validate_request()`, `create_workspace_snapshot()`, `snapshot_tree()`, `diff_snapshots()`, `redact_text()`, `atomic_write_json()`, `read_json()`.
- `TaskRequest` fields: `task_id`, `request_id`, `provider`, `mode`, `source_cwd`, `task_text`, `read_paths`, `write_paths`, `verify_commands`, `timeout_seconds`, `max_turns`, `created_at`.

- [ ] **Step 1: Write failing validation and snapshot tests**

```python
def test_review_snapshot_copies_only_authorized_files_and_protects_source(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "allowed.txt").write_text("before")
    (source / "secret.txt").write_text("outside")
    request = make_request(source, read_paths=("allowed.txt",))
    paths = task_paths(tmp_path / "state", request.task_id)
    create_workspace_snapshot(request, paths)
    (paths.workspace / "allowed.txt").write_text("changed")
    assert (source / "allowed.txt").read_text() == "before"
    assert not (paths.workspace / "secret.txt").exists()


def test_validation_rejects_absolute_parent_and_symlink_paths(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "target").write_text("x")
    (source / "link").symlink_to(source / "target")
    for bad in ("/etc/passwd", "../outside", "link"):
        with pytest.raises(ValidationError):
            validate_request(make_request(source, read_paths=(bad,)))


def test_write_paths_must_be_within_read_paths(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "src").mkdir()
    with pytest.raises(ValidationError, match="write path"):
        validate_request(
            make_request(source, read_paths=("README.md",), write_paths=("src",))
        )


def test_redaction_happens_before_logs_are_written():
    text = "OPENAI_API_KEY=sk-test-secret Authorization: Bearer abc.def.ghi"
    assert "sk-test-secret" not in redact_text(text)
    assert "abc.def.ghi" not in redact_text(text)
```

- [ ] **Step 2: Run the tests and verify the module is missing**

Run: `/opt/homebrew/bin/python3 -m pytest tests/unit/test_agent_delegate_core.py -q`

Expected: FAIL with `ModuleNotFoundError: No module named 'tools.agent_delegate'`.

- [ ] **Step 3: Implement the immutable request and path model**

Implement frozen dataclasses, ISO UTC timestamps, task directories, JSON serialization, and validation with these exact rules:

```python
VALID_PROVIDERS = frozenset({"cc", "zcode", "fake"})
VALID_MODES = frozenset({"review", "edit"})
TASK_ID_RE = re.compile(r"^task_[a-f0-9]{12}$")


@dataclass(frozen=True, slots=True)
class TaskRequest:
    task_id: str
    request_id: str
    provider: str
    mode: str
    source_cwd: str
    task_text: str
    read_paths: tuple[str, ...]
    write_paths: tuple[str, ...]
    verify_commands: tuple[tuple[str, ...], ...]
    timeout_seconds: int
    max_turns: int
    created_at: str


@dataclass(frozen=True, slots=True)
class TaskPaths:
    root: Path
    workspace: Path
    request: Path
    task_md: Path
    state: Path
    events: Path
    stdout: Path
    stderr: Path
    baseline: Path
    patch: Path
    verification: Path
    result: Path
    handoff: Path
    stop_request: Path
```

Reject empty tasks, missing/non-directory sources, duplicate or invalid request IDs, paths outside the source, symlinks at any selected path or below a selected directory, write paths outside read paths, edit mode without a write path, non-positive limits, and empty verification argv.

- [ ] **Step 4: Implement snapshots, diffs, atomic JSON, and pre-write redaction**

Copy only selected relative paths. When `.` is selected, exclude `.git`, `.env`, `.env.*`, `node_modules`, Python caches, and local state directories. Hash regular file contents with SHA-256 and record mode and size. Return added, modified, and deleted relative paths from `diff_snapshots()`.

Use `tempfile.NamedTemporaryFile(dir=target.parent, delete=False)` followed by `flush()`, `os.fsync()`, and `os.replace()` for JSON state. Apply redaction before every stdout/stderr/event write.

- [ ] **Step 5: Run core tests**

Run: `/opt/homebrew/bin/python3 -m pytest tests/unit/test_agent_delegate_core.py -q`

Expected: PASS.

- [ ] **Step 6: Commit Task 1**

```bash
git add tools/__init__.py tools/agent_delegate/__init__.py tools/agent_delegate/core.py tests/unit/test_agent_delegate_core.py
git commit -m "feat: add isolated agent task model"
```

---

### Task 2: Provider capability checks, safe argv, and output parsing

**Files:**
- Create: `tools/agent_delegate/providers.py`
- Test: `tests/unit/test_agent_delegate_providers.py`

**Interfaces:**
- Consumes: `TaskRequest`, `TaskPaths` from Task 1.
- Produces: `ProviderConfig`, `DoctorCheck`, `doctor_checks()`, `build_provider_argv()`, `parse_provider_line()`, `extract_final_result()`.

- [ ] **Step 1: Write failing provider argument tests**

```python
def test_cc_review_argv_is_restricted_and_noninteractive(request, paths):
    argv = build_provider_argv(request_for(request, provider="cc"), paths, config())
    assert argv[0] == "/opt/homebrew/bin/claude"
    assert "--restricted" in argv
    assert pair(argv, "--permission-mode") == "plan"
    assert pair(argv, "--output-format") == "stream-json"
    assert "--dangerously-skip-permissions" not in argv
    assert "--background" not in argv
    assert request.task_text not in argv


def test_zcode_review_argv_never_uses_yolo(request, paths):
    argv = build_provider_argv(request_for(request, provider="zcode"), paths, config())
    assert argv[:2] == [config().node, config().zcode_script]
    assert pair(argv, "--mode") == "plan"
    assert "yolo" not in argv
    assert pair(argv, "--cwd") == str(paths.workspace)


def test_cc_result_parser_requires_result_event():
    lines = [json.dumps({"type": "assistant", "message": {"content": []}})]
    assert extract_final_result("cc", lines) is None
    lines.append(json.dumps({"type": "result", "result": "bounded review"}))
    assert extract_final_result("cc", lines) == "bounded review"
```

- [ ] **Step 2: Run tests and verify failure**

Run: `/opt/homebrew/bin/python3 -m pytest tests/unit/test_agent_delegate_providers.py -q`

Expected: FAIL because `providers.py` does not exist.

- [ ] **Step 3: Implement provider discovery and doctor checks**

Use absolute paths when available:

```python
DEFAULT_CC = "/opt/homebrew/bin/claude"
DEFAULT_NODE = "/opt/homebrew/Cellar/node@22/22.22.1_1/bin/node"
DEFAULT_ZCODE = "/Applications/ZCode.app/Contents/Resources/glm/zcode.cjs"
```

Allow environment overrides named `AGENT_DELEGATE_CC_BIN`, `AGENT_DELEGATE_NODE_BIN`, and `AGENT_DELEGATE_ZCODE_SCRIPT`. `doctor` runs only `--version` and ZCode `doctor --json`; it never sends a prompt. Report missing executables and observed versions without reading credentials.

- [ ] **Step 4: Implement safe command builders**

CC review argv must include:

```text
--restricted --safe-mode --permission-mode plan
--tools Read,Glob,Grep
--disallowedTools Agent,Task,Bash,Edit,Write,NotebookEdit,mcp__*
--strict-mcp-config --mcp-config {"mcpServers":{}}
--disable-slash-commands --max-turns N
--output-format stream-json --verbose -p
```

Pass CC task text through stdin. For ZCode review, use `--cwd`, `--mode plan`, `--max-turns`, `--print`, `--json`, `--no-color`, and a deny list containing `Bash,Edit,Write,Agent,Task,mcp__*`; pass the prompt through `--prompt` because the bundled help does not document stdin prompts.

For this first version, `build_provider_argv()` rejects real-provider edit mode with `ValidationError("edit mode is not enabled for real providers in v1")`. The fake provider remains able to simulate changes in tests.

- [ ] **Step 5: Implement tolerant parsers without inventing progress**

Parse CC JSONL event types and take the final text only from the final `type=result` object. For ZCode, accept either one JSON object or JSONL and search these keys in order: `result`, `output`, `text`, `message`; recursively accept string content. Unknown events are recorded with `activity="provider event"`; plain text is recorded as output but cannot alone satisfy structured-result completion for ZCode.

- [ ] **Step 6: Run provider tests and commit**

Run: `/opt/homebrew/bin/python3 -m pytest tests/unit/test_agent_delegate_providers.py -q`

Expected: PASS.

```bash
git add tools/agent_delegate/providers.py tests/unit/test_agent_delegate_providers.py
git commit -m "feat: add guarded CC and ZCode adapters"
```

---

### Task 3: Foreground runner, evidence, completion semantics, and process-group stop

**Files:**
- Create: `tools/agent_delegate/runner.py`
- Create: `tests/fixtures/fake_agent_provider.py`
- Test: `tests/unit/test_agent_delegate_runner.py`

**Interfaces:**
- Consumes: core task/snapshot functions and provider argv/parsers.
- Produces: `run_task(state_root: Path, task_id: str) -> int`, `request_stop(paths, reason)`, `recover_interrupted_tasks(state_root)`.

- [ ] **Step 1: Add a fake provider with explicit scenarios**

The fixture accepts `--scenario normal|empty|fail|stderr-flood|partial-json|ignore-term|write-inside|write-outside`, writes deterministic JSONL, optionally modifies its cwd, and returns controlled exit codes. `ignore-term` installs a SIGTERM handler and sleeps until killed.

- [ ] **Step 2: Write failing runner tests**

```python
def test_exit_zero_without_result_is_failed(task_factory):
    task = task_factory(scenario="empty")
    assert run_task(task.state_root, task.task_id) == 1
    state = read_json(task.paths.state)
    assert state["state"] == "failed"
    assert state["reason"] == "result_missing"


def test_scope_violation_cannot_complete(task_factory):
    task = task_factory(mode="edit", write_paths=("allowed",), scenario="write-outside")
    run_task(task.state_root, task.task_id)
    state = read_json(task.paths.state)
    assert state["state"] == "failed"
    assert state["reason"] == "scope_violation"


def test_timeout_escalates_and_records_cleanup(task_factory):
    task = task_factory(scenario="ignore-term", timeout_seconds=1)
    run_task(task.state_root, task.task_id)
    state = read_json(task.paths.state)
    assert state["state"] == "timed_out"
    assert state["cleanup_status"] == "confirmed"


def test_large_stderr_does_not_deadlock(task_factory):
    task = task_factory(scenario="stderr-flood")
    assert run_task(task.state_root, task.task_id) == 0
```

- [ ] **Step 3: Implement runner ownership and streaming**

The runner is the sole writer of `state.json` after startup. Acquire a non-blocking `fcntl.flock` on a canonical-workspace hash and hold it through snapshot comparison, verification, cleanup, and final writes. Spawn the provider with `start_new_session=True`, `stdin=PIPE`, `stdout=PIPE`, `stderr=PIPE`, `text=False`, and `close_fds=True`.

Drain stdout and stderr concurrently with two daemon reader threads feeding a bounded `queue.Queue`. Decode with UTF-8 replacement, buffer incomplete lines, cap one event at 256 KiB, remove ANSI control sequences, redact before disk writes, and update separate `runner_heartbeat_at` and `provider_output_at` fields.

- [ ] **Step 4: Implement stop and timeout**

Poll the stop request file and monotonic deadline while consuming output. On stop or timeout, write `stopping`, call `os.killpg(provider_pgid, SIGTERM)`, keep draining for three seconds, then call `SIGKILL` if still alive. Wait and confirm that `os.killpg(pgid, 0)` raises `ProcessLookupError`; otherwise set `cleanup_status` to `incomplete` or `unknown` and never return completed.

- [ ] **Step 5: Implement evidence and final status**

After cleanup, compare the workspace to `baseline.json`; calculate scope violations from runner-observed paths. Run only stored verification argv with `shell=False`, a 120-second command timeout, the isolated workspace as cwd, and a filtered environment. Save command, exit code, redacted stdout/stderr, and duration in `verification.json`.

Write `result.json` and `handoff.md` before terminal state. The handoff sections are exactly: conclusion, provider-reported changes, runner-observed changes, verification evidence, unresolved items, and next step. Set `review_status="pending"` for completed tasks.

- [ ] **Step 6: Run runner tests and commit**

Run: `/opt/homebrew/bin/python3 -m pytest tests/unit/test_agent_delegate_runner.py -q`

Expected: PASS.

```bash
git add tools/agent_delegate/runner.py tests/fixtures/fake_agent_provider.py tests/unit/test_agent_delegate_runner.py
git commit -m "feat: add detached agent task runner"
```

---

### Task 4: CLI lifecycle and token-free terminal dashboard

**Files:**
- Create: `tools/agent_delegate/cli.py`
- Create: `scripts/agent_delegate.py`
- Test: `tests/unit/test_agent_delegate_cli.py`

**Interfaces:**
- Consumes: all prior task interfaces.
- Produces: CLI commands `doctor`, `start`, `_run`, `list`, `status`, `logs`, `result`, `stop`, and `dashboard`.

- [ ] **Step 1: Write failing CLI tests**

```python
def test_dry_run_never_spawns_provider(cli, tmp_path):
    result = cli("start", "--dry-run", "--provider", "cc", "--cwd", str(tmp_path),
                 "--task", "Review README", "--read-path", "README.md")
    assert result.returncode == 0
    assert json.loads(result.stdout)["would_start"] is False


def test_request_id_is_idempotent(cli, source):
    first = cli(*start_args(source), "--request-id", "req-123")
    second = cli(*start_args(source), "--request-id", "req-123")
    assert json.loads(first.stdout)["task_id"] == json.loads(second.stdout)["task_id"]


def test_same_request_id_with_different_body_is_rejected(cli, source):
    cli(*start_args(source), "--request-id", "req-123")
    result = cli(*start_args(source, task="different"), "--request-id", "req-123")
    assert result.returncode == 2
    assert "request_id_conflict" in result.stderr


def test_dashboard_once_contains_no_percentage(cli, completed_task):
    result = cli("dashboard", "--once")
    assert completed_task.task_id in result.stdout
    assert "%" not in result.stdout
```

- [ ] **Step 2: Run tests and verify failure**

Run: `/opt/homebrew/bin/python3 -m pytest tests/unit/test_agent_delegate_cli.py -q`

Expected: FAIL because CLI files do not exist.

- [ ] **Step 3: Implement `doctor`, `start`, and internal `_run`**

`start` validates all arguments, computes a SHA-256 request fingerprint, enforces request-ID idempotency, creates `queued` state, and starts:

```python
subprocess.Popen(
    [sys.executable, script_path, "_run", "--task-id", task_id,
     "--state-root", str(state_root)],
    stdin=subprocess.DEVNULL,
    stdout=runner_log,
    stderr=runner_log,
    start_new_session=True,
    close_fds=True,
)
```

Return JSON within five seconds. `_run` is hidden from help and calls `run_task()`.

- [ ] **Step 4: Implement read-only lifecycle commands**

`list` sorts newest first. `status` prints state JSON. `logs` tails a bounded number of redacted lines. `result` prints `handoff.md` by default and supports `--json` for `result.json`. `stop` atomically writes `control/stop.json`; repeating it is harmless and never signals an arbitrary PID directly.

- [ ] **Step 5: Implement dashboard**

`dashboard --once` prints a compact table. Without `--once`, clear and repaint once per configurable interval until Ctrl-C. Display task ID, provider, mode, state, elapsed time, runner heartbeat age, provider output age, latest known activity, and verification state. Never display a percentage or call a provider.

- [ ] **Step 6: Run CLI tests and detached-lifecycle fake smoke test**

Run: `/opt/homebrew/bin/python3 -m pytest tests/unit/test_agent_delegate_cli.py -q`

Then create a temporary repository and run a five-second fake task through `start`; close the initiating command, poll the state from a separate command, and verify it completes. Expected: `start` returns immediately and the task reaches `completed` without the parent command remaining open.

- [ ] **Step 7: Commit Task 4**

```bash
git add tools/agent_delegate/cli.py scripts/agent_delegate.py tests/unit/test_agent_delegate_cli.py
git commit -m "feat: add agent delegation CLI and dashboard"
```

---

### Task 5: Codex Skill, full verification, and real read-only probes

**Files:**
- Create: `.agents/skills/agent-delegate/SKILL.md`
- Test: `tests/unit/test_agent_delegate_skill.py`
- Modify: `docs/superpowers/specs/2026-09-13-cross-agent-delegation-design.md`

**Interfaces:**
- Consumes: `scripts/agent_delegate.py` CLI.
- Produces: user phrases “交给 CC”, “让 ZCode 复核”, “查看派工进度”, and “停止派工任务” mapped to guarded CLI commands.

- [ ] **Step 1: Read the skill-creator instructions and write the failing contract test**

The test reads `SKILL.md` and asserts it names the exact CLI path, defaults to review, requires read paths, refuses real-provider edit mode in v1, uses `dashboard` instead of model polling, reads `handoff.md` before evidence, and never contains dangerous bypass flags.

- [ ] **Step 2: Create the project Skill**

The Skill workflow is:

1. Restate goal, read scope, prohibited actions, and acceptance evidence.
2. Run `doctor`; stop on capability failure.
3. Run `start --dry-run`; inspect effective permissions and paths.
4. Start exactly one provider and return its task ID plus the token-free dashboard command.
5. Do not poll through model turns; let the user inspect the dashboard.
6. On explicit review request, read `handoff.md`, then inspect only relevant patch/files/verification evidence.
7. Never auto-resume, retry, apply, commit, or dispatch another provider.

- [ ] **Step 3: Run focused and full static verification**

```bash
/opt/homebrew/bin/python3 -m pytest \
  tests/unit/test_agent_delegate_core.py \
  tests/unit/test_agent_delegate_providers.py \
  tests/unit/test_agent_delegate_runner.py \
  tests/unit/test_agent_delegate_cli.py \
  tests/unit/test_agent_delegate_skill.py -q
/opt/homebrew/bin/python3 -m ruff check tools/agent_delegate scripts/agent_delegate.py tests/unit/test_agent_delegate_*.py
```

Expected: all tests pass and Ruff reports no errors.

- [ ] **Step 4: Run CC read-only probe in a temporary Git repository**

Create a temporary repository containing only `README.md`, record its SHA-256, dispatch CC in review mode with `--read-path README.md`, and watch it using the terminal dashboard. Expected: task reaches `completed`, `handoff.md` contains a non-empty review, and the source hash is unchanged.

- [ ] **Step 5: Run ZCode contract probe in a separate temporary Git repository**

Run `doctor`, then dispatch ZCode in review mode with a task that only summarizes `README.md`. Record whether `--json` is one object or JSONL, which fields contain the final answer and session ID, and whether plan mode attempts a permission wait. If parsing or permission behavior differs, update only the ZCode adapter and its fixtures, rerun all focused tests, and keep real-workspace ZCode disabled until the probe passes.

- [ ] **Step 6: Verify source repository boundaries and document observed capabilities**

Run `git status --short` and confirm no files outside this plan’s paths changed because of the probes. Add an “Observed runtime contract” section to the design with the CC/ZCode outcomes, exact versions, and any remaining limitation. Do not turn a failed probe into a claimed success.

- [ ] **Step 7: Commit Task 5**

```bash
git add .agents/skills/agent-delegate/SKILL.md tests/unit/test_agent_delegate_skill.py \
  docs/superpowers/specs/2026-09-13-cross-agent-delegation-design.md
git commit -m "feat: add guarded cross-agent delegation skill"
```

## Plan self-review

- Every design requirement maps to a task: isolation and scope enforcement (Task 1), provider restrictions and parsing (Task 2), completion and stopping (Task 3), background lifecycle and dashboard (Task 4), Codex workflow and real probes (Task 5).
- Real-model calls occur only after deterministic fake-provider tests pass.
- Real-provider editing is deliberately rejected in v1; this removes an unverified security surface while preserving the requested review/dispatch proof.
- All commands use argument arrays and task-owned copies; the dirty source workspace is never mutated by a provider.
- There are no placeholders, automatic retries, online approvals, background-provider nesting, or invented completion percentages.
