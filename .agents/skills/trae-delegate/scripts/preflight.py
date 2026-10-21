#!/usr/bin/env python3
"""Read-only local capability probe; never emit login output or credential content."""
import json
from pathlib import Path
import shutil
import subprocess
import sys

def main():
    cli = shutil.which("traecli")
    fallback = Path.home() / ".local/bin/traecli"
    if not cli and fallback.is_file():
        cli = str(fallback)
    result = {"schema": "trae-preflight/1", "model_task_executed": False}
    if not cli:
        print(json.dumps({**result, "status": "not_installed"}))
        return 2
    try:
        def run(*args):
            return subprocess.run([cli, *args], capture_output=True, text=True, timeout=15)
        version, top, help_, auth = run("--version"), run("--help"), run("exec", "--help"), run("login", "status")
        result["version"] = version.stdout.strip().splitlines()[0] if version.stdout.strip() else "unknown"
        flags = ["--json", "--ephemeral", "--output-schema", "--output-last-message", "--sandbox", "--skip-git-repo-check"]
        result["supported_flags"] = {f: f in help_.stdout for f in flags}
        result["supported_flags"]["--no-daemon"] = "--no-daemon" in top.stdout
        result["login_status_exit_code"] = auth.returncode
        if any(x.returncode for x in (version, top, help_)) or not all(result["supported_flags"].values()):
            result["status"] = "capability_unverified"; code = 3
        elif auth.returncode != 0:
            result["status"] = "authentication_unconfirmed"; code = 2
        else:
            result["status"] = "local_preconditions_only_service_entitlement_untested"; code = 0
    except (OSError, subprocess.TimeoutExpired) as e:
        result["status"] = "probe_failed"
        result["error_type"] = type(e).__name__
        code = 3
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return code
if __name__ == "__main__":
    sys.exit(main())
