"""List newer report evidence without guessing object links or promoting results."""
from datetime import datetime, timezone
from pathlib import Path
import re

from lei_signal.api.experiment_reports import scan_reports


def extend_intake(root: Path, progress: dict) -> dict:
    reviewed_day = progress["reviewedAt"][:10]
    known = {s.get(key) for s in progress["sources"] for key in ("path", "reportPath")}
    items = []
    for report in scan_reports(root):
        path = report["name"]
        # File modification time is not a research event date. Only explicit
        # report filename dates qualify for this incremental evidence inbox.
        day = re.search(r"\d{4}-\d{2}-\d{2}", Path(path).stem)
        if (not path.startswith("docs/experiments/") or not day
                or day[0] < reviewed_day or path in known or report.get("isPrompt")):
            continue
        items.append({"path": path, "title": report["title"], "date": day[0],
                      "category": report["category"], "status": "pending_review"})
    return {**progress, "intake": {"reviewedThrough": reviewed_day,
            "checkedAt": datetime.now(timezone.utc).isoformat(), "items": items}}
