"""Read-only context preview. Does not import the full application or open a DB."""
from fastapi import FastAPI
from lei_signal.api.routes.fundamentals import router
from lei_signal.fundamentals.service import FundamentalsService
app = FastAPI()
app.state.fundamentals_service = FundamentalsService()
app.include_router(router)
