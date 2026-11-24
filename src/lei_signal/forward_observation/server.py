"""Local-only API process owning one observation worker.

This avoids restarting the shared market API to publish an independent research
feature. Restarting this process restores the same immutable ledger; it does not
provide OS login/startup installation.
"""

from __future__ import annotations

import os
import subprocess
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from lei_signal.api.routes.fwd_ledger import router

from .runner import ROOT


@asynccontextmanager
async def lifespan(app: FastAPI):
    worker = None
    if os.environ.get("LEI_FORWARD_NO_WORKER") != "1":
        worker = subprocess.Popen(
            [sys.executable, "-m", "lei_signal.forward_observation.runner", "--watch"],
            cwd=ROOT,
        )
    try:
        yield
    finally:
        if worker and worker.poll() is None:
            worker.terminate()
            try:
                worker.wait(timeout=35)
            except subprocess.TimeoutExpired:
                worker.kill()
                worker.wait()


app = FastAPI(title="LeiSignal 策略前向观察", lifespan=lifespan)
app.include_router(router)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("LEI_FORWARD_PORT", "8018")))
