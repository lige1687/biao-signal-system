"""Append five original-goal evidence notes without copying full histories."""
import datetime
import hashlib
import json
import urllib.request
from pathlib import Path

RAW = Path(__file__).parent
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
IDS = {"okr-ff1e0a86fbac", "okr-4f4157e2957e", "okr-57eb3f28e526", "D-evidence", "D-tracking"}


def get():
    with OPENER.open("http://127.0.0.1:8000/api/upgrades", timeout=30) as response:
        return {x["id"]: x for x in json.load(response)["items"]}


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def main():
    plan = json.loads((RAW / "five-evidence-notes-plan.json").read_text())
    assert set(plan["notes"]) == IDS
    receipts = []
    for goal_id, note in plan["notes"].items():
        before = get()[goal_id]
        exists = any(x.get("note") == note for x in before["history"])
        protected = {k: v for k, v in before.items() if k not in {"history", "updated_at", "version"}}
        history_hash = hashlib.sha256(json.dumps(before["history"], ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        save(RAW / ("note-intent-" + goal_id + ".json"), {
            "goal_id": goal_id, "before_version": before["version"], "note": note,
            "scope": plan["scope"], "protected_fields": protected,
            "history_entries": len(before["history"]), "history_sha256": history_hash,
            "full_history_not_duplicated": True})
        error = None
        if not exists:
            request = urllib.request.Request("http://127.0.0.1:8000/api/upgrades/" + goal_id + "/actions",
                data=json.dumps({"version": before["version"], "action": "note", "note": note,
                                 "scope": plan["scope"]}).encode(),
                headers={"Content-Type": "application/json"}, method="POST")
            try:
                with OPENER.open(request, timeout=30) as response:
                    json.load(response)
            except Exception as exc:
                error = type(exc).__name__ + ": " + str(exc)
        # Always recover the actual state before considering any repeat.
        after = get()[goal_id]
        actual_count = sum(x.get("note") == note for x in after["history"])
        if actual_count != 1:
            save(RAW / ("note-failure-" + goal_id + ".json"), {
                "goal_id": goal_id, "error": error, "actual_note_count": actual_count,
                "actual_version": after["version"], "not_retried": True})
            raise RuntimeError("Note was not proven unique after actual state readback: " + goal_id)
        assert {k: after[k] for k in protected} == protected
        changed = [k for k in before if before[k] != after[k]]
        assert set(changed) <= {"history", "updated_at", "version"}
        if not exists:
            assert after["history"][:-1] == before["history"]
            assert after["version"] == before["version"] + 1
        receipts.append({"goal_id": goal_id, "version_before": before["version"],
            "version_after": after["version"], "status": after["status"], "progress": after["progress"],
            "actual_note_readback": True, "protected_fields_preserved": True,
            "history_prefix_preserved": True, "changed_fields": changed,
            "reused_existing_identical_note": exists, "response_error": error})
        save(RAW / "five-evidence-notes-readback.json", {"at": datetime.datetime.now(
            datetime.timezone(datetime.timedelta(hours=8))).isoformat(), "result_commit": plan["result_commit"],
            "receipts": receipts})
    print(json.dumps(receipts, ensure_ascii=False))


if __name__ == "__main__":
    main()
