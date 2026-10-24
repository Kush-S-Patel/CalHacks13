"""
SwarmCFO System of Work — the Hyphenate blueprint.

Records (bank, invoices, ERP) hold the truth about the business.
This package holds the truth about the *work*:
  work items · decisions · approvals · learned policies · append-only audit.

Four questions answered in code:
  WORLD  — where agents act (work items over synced golden records)
  TIME   — what they remember next quarter (policies + precedents)
  TEAM   — who they work with (actors, roles, separation of duties)
  LIMITS — what they may do, and can prove why (can() + audit diffs)
"""

from sow.audit import AuditLog
from sow.gateway import Gateway
from sow.learn import PolicyLearner
from sow.models import Actor, Policy, Precedent, WorkItem
from sow.roles import ROLES, can
from sow.scoring import score_run
from sow.store import SystemOfWork
from sow.transitions import TRANSITIONS, transition

__all__ = [
    "Actor",
    "AuditLog",
    "Gateway",
    "Policy",
    "PolicyLearner",
    "Precedent",
    "ROLES",
    "SystemOfWork",
    "TRANSITIONS",
    "WorkItem",
    "can",
    "score_run",
    "transition",
]