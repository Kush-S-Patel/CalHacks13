"""Assemble deliverable + job-cost package for human review."""

from __future__ import annotations

from missions.models import Mission


def build_deliverable(mission: Mission) -> str:
    ledger = mission.job_ledger()
    lines = [
        f"# Intelligence report — {mission.client}",
        "",
        f"**Brief:** {mission.brief}",
        "",
        "## Findings",
    ]
    verified = [e for e in mission.evidence if e.verified]
    pending = [e for e in mission.evidence if e.verified is None]
    failed = [e for e in mission.evidence if e.verified is False]

    if verified:
        for e in verified:
            lines.append(f"- {e.claim} _(source: {e.source}; conf {e.confidence:.2f})_")
    else:
        for e in mission.evidence[:8]:
            lines.append(f"- {e.claim} _(source: {e.source})_")

    lines.extend(["", "## Evidence index"])
    for e in mission.evidence:
        flag = "verified" if e.verified else ("unsupported" if e.verified is False else "proposed")
        lines.append(f"- `{e.id}` [{flag}] {e.url_or_ref or e.source} — {e.claim[:100]}")

    lines.extend(
        [
            "",
            "## Job cost ledger",
            f"- Quoted client price: **${ledger['quote_cents']/100:,.2f}**",
            f"- Max authorized tool spend: **${ledger['max_spend_cents']/100:,.2f}**",
            f"- Actual tool spend: **${ledger['spent_cents']/100:,.2f}**",
            f"- Remaining budget: **${ledger['remaining_cents']/100:,.2f}**",
            f"- Implied margin (quote − tool spend): **${ledger['margin_cents']/100:,.2f}** ({ledger['margin_pct']}%)",
            "",
            "### Spend by agent",
        ]
    )
    for agent, cents in (ledger.get("by_agent_cents") or {}).items():
        lines.append(f"- {agent}: ${cents/100:,.2f}")
    lines.append("")
    lines.append("### Spend by tool")
    for tool, cents in (ledger.get("by_tool_cents") or {}).items():
        lines.append(f"- {tool}: ${cents/100:,.2f}")

    if mission.denials:
        lines.extend(["", "## Budget denials (audited)"])
        for d in mission.denials:
            lines.append(f"- DENIED {d.agent}/{d.tool} ${d.amount_cents/100:.2f} — {d.reason}")

    if mission.exceptions:
        lines.extend(["", "## Unresolved exceptions"])
        for ex in mission.exceptions:
            lines.append(f"- {ex}")

    lines.extend(
        [
            "",
            "## Constraints honored",
            "- Did not bill the client.",
            "- Did not submit externally.",
            "- Tool spend enforced in code (BudgetController).",
            "",
            f"_Status: {mission.status} · evidence {len(mission.evidence)} "
            f"(verified {len(verified)}, pending {len(pending)}, unsupported {len(failed)})_",
        ]
    )
    return "\n".join(lines)


def package_summary(mission: Mission) -> dict:
    return {
        "mission_id": mission.id,
        "status": mission.status,
        "job_ledger": mission.job_ledger(),
        "exceptions": mission.exceptions,
        "denial_count": len(mission.denials),
        "evidence_count": len(mission.evidence),
        "deliverable_preview": (mission.deliverable_md or "")[:500],
    }
