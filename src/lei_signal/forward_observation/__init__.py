"""Prospective, simulated strategy observation. No broker integration."""

from .service import build_dashboard, initialize, process_observation

__all__ = ["initialize", "process_observation", "build_dashboard"]
