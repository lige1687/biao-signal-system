"""零依赖 .env 加载器。

仅用于本地 / launchd 注入配置：把仓库根目录的 ``.env`` 读入 ``os.environ``，
但**不覆盖** shell 或 launchd 已设置的变量（后者优先）。

``.env`` 必须被 ``.gitignore`` 忽略（已配置），切勿把真实 webhook / 密钥提交进仓库。
"""
from __future__ import annotations

import os
from pathlib import Path

_DEFAULT_ENV_NAME = ".env"


def _repo_root() -> Path:
    # 不依赖固定层级：从本文件向上找到含 .env.example / pyproject.toml 的仓库根。
    here = Path(__file__).resolve().parent
    for candidate in (here, *here.parents):
        if (candidate / ".env.example").is_file() or (
            candidate / "pyproject.toml"
        ).is_file():
            return candidate
    # 兜底：沿用原相对约定（src/lei_signal/env.py -> parents[2]）
    return here.parents[1]


def load_env(*, path: str | os.PathLike[str] | None = None) -> None:
    """读取 ``.env`` 并补充 ``os.environ``（跳过已存在的键）。幂等可重复调用。"""
    env_path = Path(path) if path else _repo_root() / _DEFAULT_ENV_NAME
    if not env_path.is_file():
        return
    with env_path.open("r", encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
                value = value[1:-1]
            if key and key not in os.environ:
                os.environ[key] = value


__all__ = ["load_env"]
