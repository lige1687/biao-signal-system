"""factor_lab：通用因子/信号研究工具（离线、合成、带测试）。

公开入口（spec §4.1）：
- ``adapters.calculate_batch`` → ResearchBatch
- ``diagnostics.evaluate_predictive``
- ``validation.audit_validation``
- ``attribution.explain_strategy``
- ``runner.run_protocol``

既有入口正式输出仍仅 synthetic，不提供跳过核验开关。
新增 evaluate_frozen_rank_ic 使用独立冻结合同，复用既有数学核；无生产授权。
"""

from lei_signal.research.factor_lab.contracts import (
    EXIT_IDENTITY_FORMAT,
    EXIT_INSUFFICIENT_DATA,
    EXIT_OK,
    IdentityFormatError,
    InsufficientDataError,
    ResearchBatch,
)
from lei_signal.research.factor_lab.rank_ic_evaluation import (
    RankICCheckpoint,
    RankICColumns,
    RankICContract,
    RankICEvaluation,
    RankICLabelWindow,
    RankICModelFold,
    RankICRealBinding,
    RankICScore,
    RankICUniverse,
    evaluate_frozen_rank_ic,
    frame_sha256,
    session_sequence_sha256,
)

__all__ = [
    "EXIT_IDENTITY_FORMAT",
    "EXIT_INSUFFICIENT_DATA",
    "EXIT_OK",
    "IdentityFormatError",
    "InsufficientDataError",
    "ResearchBatch",
    "RankICCheckpoint",
    "RankICColumns",
    "RankICContract",
    "RankICEvaluation",
    "RankICLabelWindow",
    "RankICModelFold",
    "RankICRealBinding",
    "RankICScore",
    "RankICUniverse",
    "evaluate_frozen_rank_ic",
    "frame_sha256",
    "session_sequence_sha256",
]
