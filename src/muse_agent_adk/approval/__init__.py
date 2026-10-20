"""approval: risk-tiered HITL gate, enforced via ADK before_tool_callback.

Default posture differs from muse-agent on purpose: no approver wired
in means write/exec are DENIED (fail closed), not auto-approved.
"""
from muse_agent_adk.approval.gate import ApprovalGate
from muse_agent_adk.approval.policy import (ApprovalPolicy, Approver,
                                              Decision, RiskLevel,
                                              auto_approver, deny_approver)

__all__ = [
    "ApprovalPolicy", "ApprovalGate", "Approver", "Decision", "RiskLevel",
    "auto_approver", "deny_approver",
]
