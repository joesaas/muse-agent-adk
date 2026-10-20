"""Risk-tiered approval.

  read  -> auto-approved (looking is free)
  write -> needs approval unless config/policy says otherwise
  exec  -> needs approval, always asked explicitly

The approver is a callback: the CLI asks the user in the terminal, a
chat front-end shows a card, tests inject auto/deny. Policy never
knows which — that separation is what makes HITL portable.

DELIBERATE DIFFERENCE from muse-agent: there, a session built without
an approver silently fell back to ``auto_approver`` (fail-open — the
module review of the original project flagged this as a defect: any
front-end that forgot to pass an approver got silent consent). Here,
``approver=None`` means DENY for write/exec. Consent must be wired in
explicitly; forgetting is safe instead of dangerous.
"""
from __future__ import annotations

from enum import Enum
from typing import Callable

from muse_agent_adk.core.types import ToolCall


class RiskLevel(str, Enum):
    READ = "read"
    WRITE = "write"
    EXEC = "exec"


class Decision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"


Approver = Callable[[ToolCall, RiskLevel], bool]


def auto_approver(call: ToolCall, risk: RiskLevel) -> bool:
    return True


def deny_approver(call: ToolCall, risk: RiskLevel) -> bool:
    return False


class ApprovalPolicy:
    def __init__(self, approver: Approver | None = None,
                 auto_approve_write: bool = False) -> None:
        self.approver = approver
        self.auto_approve_write = auto_approve_write

    def check(self, call: ToolCall, risk: str) -> Decision:
        level = RiskLevel(risk)
        if level is RiskLevel.READ:
            return Decision.ALLOW
        if level is RiskLevel.WRITE and self.auto_approve_write:
            return Decision.ALLOW
        if self.approver is None:
            # Fail closed: no approver wired in means nobody consented.
            return Decision.DENY
        return Decision.ALLOW if self.approver(call, level) else Decision.DENY
