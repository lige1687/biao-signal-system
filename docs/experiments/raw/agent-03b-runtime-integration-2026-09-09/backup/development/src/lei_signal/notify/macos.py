"""macOS best-effort 通知投递器。"""
from __future__ import annotations

import subprocess

from lei_signal.notify.base import NotificationPayload


class MacNotifier:
    def __init__(self, *, dry_run: bool = False) -> None:
        self.dry_run = dry_run

    def send(self, payload: NotificationPayload) -> bool:
        if self.dry_run:
            print(f"[dry-run] 通知 | {payload.title}: {payload.body_md}")
            return True
        body = payload.body_md.replace('"', "'")
        for cmd in (
            ["terminal-notifier", "-title", payload.title, "-message", body],
            ["osascript", "-e", f'display notification "{body}" with title "{payload.title}"'],
        ):
            try:
                subprocess.run(cmd, check=False, timeout=5)  # noqa: S603
                return True
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
        return False


__all__ = ["MacNotifier"]
