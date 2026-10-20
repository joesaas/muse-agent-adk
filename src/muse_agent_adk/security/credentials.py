"""Credential access by *name*, never by value-in-code.

Two modes behind one interface:
  - direct: read an environment variable (local development)
  - surrogate: in hosted runtimes (Muse-style), a broker can hand out
    short-lived surrogate tokens that an egress proxy swaps for the
    real secret, so the agent process never holds the real value.
    Implement get() with your broker client to use that mode; the
    rest of the system cannot tell the difference.
"""
from __future__ import annotations

import os


class CredentialStore:
    def __init__(self, mode: str = "env") -> None:
        if mode not in ("env", "surrogate"):
            raise ValueError(f"unknown credential mode: {mode}")
        self.mode = mode

    def get(self, name: str) -> str | None:
        if self.mode == "env":
            return os.environ.get(name)
        # Surrogate mode is an integration seam: plug a broker client
        # here. Returning None (not raising) keeps callers honest:
        # they must handle "not connected" as a normal state.
        return None

    def has(self, name: str) -> bool:
        return bool(self.get(name))
