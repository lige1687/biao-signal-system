"""Save only actual current-round CUA observations; no browser or network calls."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

out = Path(__file__).resolve().parent
root = out.parents[3]
thread = "01a0ebfb-fd80-7c62-97c9-ac24d20f58e4"
task = "sentiment-standard-review-20260929"
url = "https://chatgpt.com/c/6ab1f426-5850-83ee-8eef-bf77c8d7c697"
cli = ["node", "/Users/yongbiaoli/.agents/skills/codex-with-chatgpt/core/bin/c2c.js"]
env = os.environ.copy()
env["C2C_STATE_DIR"] = str(out / "c2c-state")
payload = json.load(sys.stdin)
items = payload.get("observations", [payload])
for item in items:
    assert item["status"] in ("thinking", "reply-ready", "unavailable", "login-required")
    observation = {
        "taskId": task, "threadId": thread, "round": 1,
        "source": "codex-in-app-browser", "conversationUrl": url,
        "observationId": item["observationId"],
        "observedAt": item["observedAt"], "status": item["status"],
    }
    text = item.get("text", "")
    if text:
        observation["progressFingerprint"] = hashlib.sha256(text.encode()).hexdigest()
    with (out / "review-progress-observations.jsonl").open("a") as f:
        f.write(json.dumps(observation, ensure_ascii=False) + "\n")
    (out / "current-observation.json").write_text(json.dumps(observation) + "\n")
    age = datetime.datetime.now(datetime.timezone.utc) - datetime.datetime.fromisoformat(item["observedAt"].replace("Z", "+00:00"))
    if age.total_seconds() > 60:
        with (out / "expired-observations.jsonl").open("a") as f:
            f.write(json.dumps({"observation": observation, "age_at_persistence_seconds": age.total_seconds(),
                                "status": "raw_saved_only_not_submitted_as_fresh"}) + "\n")
        continue
    result = subprocess.run(cli + ["review", "observe", "-w", str(root), "--thread", thread,
                                  "--evidence", str(out / "current-observation.json"), "--json"],
                            env=env, capture_output=True, text=True)
    with (out / "cli-observe-results.jsonl").open("a") as f:
        f.write(json.dumps({"observation_id": item["observationId"], "exit_code": result.returncode,
                            "stdout": result.stdout, "stderr": result.stderr}) + "\n")
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    if item["status"] == "reply-ready":
        assert item.get("complete") is True and text
        evidence = {k: v for k, v in observation.items() if k != "progressFingerprint"}
        evidence.pop("status")
        evidence.update({"role": "assistant", "complete": True,
                         "messageFingerprint": hashlib.sha256((out / "prompt.txt").read_bytes()).hexdigest(),
                         "replyFingerprint": hashlib.sha256(text.encode()).hexdigest(), "text": text})
        (out / "pro-reply-verbatim.txt").write_text(text)
        (out / "reply-evidence.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n")
        result = subprocess.run(cli + ["review", "reply", "-w", str(root), "--thread", thread,
                                      "--evidence", str(out / "reply-evidence.json"), "--json"],
                                env=env, capture_output=True, text=True)
        (out / "reply-validation.json").write_text(json.dumps({"exit_code": result.returncode,
                                                               "stdout": result.stdout, "stderr": result.stderr},
                                                              ensure_ascii=False, indent=2) + "\n")
        if result.returncode:
            raise RuntimeError(result.stderr)
        print(json.dumps({"reply_saved_and_validated": True, "chars": len(text)}, ensure_ascii=False))

result = subprocess.run(cli + ["review", "heartbeat", "-w", str(root), "--thread", thread, "--json"],
                        env=env, capture_output=True, text=True)
assert result.returncode == 0, result.stderr
with (out / "heartbeat-results.jsonl").open("a") as f:
    f.write(result.stdout.strip() + "\n")
print(result.stdout.strip())
