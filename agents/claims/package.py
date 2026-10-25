"""Draft reimbursement schedules + evidence index + exception report."""

from __future__ import annotations

from claims.models import ClaimPackage


def build_schedules(package: ClaimPackage) -> str:
    risk = package.risk
    lines = [
        f"# Reimbursement package — {package.nonprofit}",
        "",
        f"**Award:** {package.award.award_id} · CFDA {package.award.cfda}",
        f"**Funder:** {package.award.funder}",
        f"**Reporting period:** {package.reporting_period}",
        f"**PoP:** {package.award.period_start} → {package.award.period_end}",
        "",
        "## Rejection risk",
    ]
    if risk:
        lines.extend(
            [
                f"- **Score:** {risk.score}/100 · **Band:** {risk.band}",
                f"- **Recommendation:** {risk.recommendation}",
                "",
                "### Risk drivers (corpus-backed)",
            ]
        )
        for d in risk.drivers[:12]:
            lines.append(f"- `{d.get('exception')}` (+{d.get('points', 0)}) — sources: {d.get('sources')}")
        lines.append("")
        lines.append(
            "_Priors from FAC findings, Covered CA denial taxonomy, and Grants.gov-shaped "
            "submission rejections (see data/train_data/claims/SOURCES.md)._"
        )
    lines.extend(["", "## Claimed expenditures by budget line"])
    by_line: dict[str, int] = {}
    for m in package.matches:
        if {"duplicate_expense", "excluded_from_claim"} & set(m.exception_codes):
            continue
        by_line[m.budget_line] = by_line.get(m.budget_line, 0) + m.amount_cents
    for line, cents in sorted(by_line.items()):
        cap = package.award.budget_lines.get(line)
        cap_s = f" / cap ${cap/100:,.2f}" if cap is not None else ""
        lines.append(f"- **{line}:** ${cents/100:,.2f}{cap_s}")

    tot = package.totals or {}
    lines.extend(
        [
            "",
            "## Reconciliation (deterministic)",
            f"- Eligible claim: **${(tot.get('eligible_cents') or tot.get('claimed_cents') or 0)/100:,.2f}**",
            f"- GL export total: **${(tot.get('gl_cents') or 0)/100:,.2f}**",
            f"- Duplicate lines held out: **${(tot.get('duplicate_cents') or 0)/100:,.2f}**",
            f"- Excluded / protected: **${(tot.get('excluded_cents') or 0)/100:,.2f}**",
            f"- Recon gap: **${(tot.get('recon_gap_cents') or 0)/100:,.2f}**",
            "",
            "## Transaction ↔ evidence matches",
        ]
    )
    for m in package.matches:
        ev = ",".join(m.evidence_ids) if m.evidence_ids else "NONE"
        exc = ",".join(m.exception_codes) if m.exception_codes else "—"
        lines.append(
            f"- `{m.ledger_id}` {m.date} {m.vendor} ${m.amount_cents/100:,.2f} "
            f"→ evidence [{ev}] conf={m.confidence:.2f} exceptions={exc}"
        )

    lines.extend(["", "## Evidence index"])
    for e in package.evidence:
        lines.append(f"- `{e.id}` {e.kind} · {e.filename} · linked={e.linked_ledger_id or '—'}")

    lines.extend(["", "## Unresolved exceptions (evidence-backed)"])
    if not package.exceptions:
        lines.append("- None")
    for ex in package.exceptions:
        if isinstance(ex, dict):
            lines.append(f"- **{ex.get('code')}** · {ex.get('message')} · ledger={ex.get('ledger_id', '—')}")
        else:
            lines.append(f"- {ex}")

    lines.extend(
        [
            "",
            "## Constraints",
            "- Do **not** submit to the funder from this system.",
            "- Do **not** alter the accounting ledger.",
            "- Finance manager approval required before any external filing.",
            "",
            f"_Status: {package.status} · generated for manager review_",
        ]
    )
    return "\n".join(lines)
