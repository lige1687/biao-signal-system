"""factor_lab：通用因子/信号研究工具（离线、合成、带测试）。

公开入口（spec §4.1）：
- ``adapters.calculate_batch`` → ResearchBatch
- ``diagnostics.evaluate_predictive``
- ``validation.audit_validation``
- ``attribution.explain_strategy``
- ``runner.run_protocol``

本轮正式输出仅 synthetic；不提供跳过核验开关；无生产授权。
"""
from lei_signal.research.factor_lab.contracts import (
    EXIT_IDENTITY_FORMAT,
    EXIT_INSUFFICIENT_DATA,
    EXIT_OK,
    IdentityFormatError,
    InsufficientDataError,
    ResearchBatch,
)

__all__ = [
    "EXIT_IDENTITY_FORMAT",
    "EXIT_INSUFFICIENT_DATA",
    "EXIT_OK",
    "IdentityFormatError",
    "InsufficientDataError",
    "ResearchBatch",
]
