"""Local read-only UI endpoint with one independently owned worker."""

import os
import subprocess
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from .service import ROOT, dashboard


@asynccontextmanager
async def lifespan(app):
    worker = None
    if os.environ.get("LEI_PORTFOLIOS_NO_WORKER") != "1":
        worker = subprocess.Popen(
            [sys.executable, "-m", "lei_signal.strategy_portfolios.runner", "--watch"], cwd=ROOT
        )
    try:
        yield
    finally:
        if worker and worker.poll() is None:
            worker.terminate()
            worker.wait(timeout=20)


app = FastAPI(title="A股美股个股策略研究", lifespan=lifespan)


@app.get("/api/strategy-portfolios")
def get_dashboard():
    return dashboard()


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8028)
