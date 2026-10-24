"""
Run a mission: research → extract → verify → package under BudgetController.

Uses deterministic metered stubs by default (hackathon-reliable).
Optional Claude turns are metered via claude_turn charges when key present.
"""

from __future__ import annotations

import logging
from typing import Any

from missions.budget import BudgetDenied, charge
from missions.models import Mission, MissionBudget, new_id, now_iso
from missions.package import build_deliverable
from missions.store import MISSIONS
from missions.tools_metered import (
    metered_compose_report,
    metered_extract_facts,
    metered_verify_claim,
    metered_web_search,
)

log = logging.getLogger("swarmcfo.missions")


def create_mission(
    *,
    client: str,
    brief: str,
    quote_cents: int,
    max_spend_cents: int,
    meta: dict[str, Any] | None = None,
) -> Mission:
    m = Mission(
        id=new_id("mission"),
        client=client,
        brief=brief,
        quote_cents=quote_cents,
        budget=MissionBudget(max_spend_cents=max_spend_cents),
        status="draft",
        meta=meta or {},
    )
    m.log.append(f"CREATED quote=${quote_cents/100:.2f} max_spend=${max_spend_cents/100:.2f}")
    MISSIONS.upsert(m)
    return m


def expand_budget(mission: Mission, additional_cents: int, *, reason: str = "owner expand") -> Mission:
    mission.budget.max_spend_cents += int(additional_cents)
    if mission.status == "held":
        mission.status = "running"
    mission.log.append(f"EXPAND +{additional_cents}c — {reason} · max now {mission.budget.max_spend_cents}c")
    mission.updated_at = now_iso()
    MISSIONS.upsert(mission)
    return mission


def _link_sow(mission: Mission, sow: Any | None) -> None:
    if sow is None:
        return
    from sow.models import SYNC
    from sow.models import Policy

    # Seed mission policies once
    if "pol-mission-001" not in sow.policies:
        sow.policies["pol-mission-001"] = Policy(
            id="pol-mission-001",
            version=1,
            title="Mission max tool spend",
            rule="Tool charges must not exceed mission.budget.max_spend_cents; denials audited.",
            condition={"type": "mission_budget"},
            action={"deny": "over_budget"},
            status="active",
            evidence=["mission_margin"],
        )
    if "pol-mission-002" not in sow.policies:
        sow.policies["pol-mission-002"] = Policy(
            id="pol-mission-002",
            version=1,
            title="No unmetered tools on missions",
            rule="Every mission tool call must go through BudgetController.charge.",
            condition={"type": "metered_only"},
            action={"require": "BudgetController"},
            status="active",
            evidence=["mission_margin"],
        )

    wi = sow.create_work(
        SYNC,
        kind="mission_run",  # type: ignore[arg-type]
        subject=mission.id,
        title=f"Mission {mission.client}: {mission.brief[:60]}",
        amount_cents=mission.budget.max_spend_cents,
        evidence=[mission.id],
        payload={
            "mission_id": mission.id,
            "quote_cents": mission.quote_cents,
            "max_spend_cents": mission.budget.max_spend_cents,
        },
    )
    mission.work_item_ids.append(wi.id)


def run_mission(
    mission: Mission,
    *,
    sow: Any | None = None,
    force_overspend_probe: bool = True,
    use_claude: bool = False,
) -> dict[str, Any]:
    """
    Deterministic orchestration under budget.
    force_overspend_probe: attempt an extra search after budget near-exhaustion to prove DENY.
    """
    mission.status = "running"
    mission.log.append("RUN start")
    _link_sow(mission, sow)

    try:
        # Optional: meter a Claude planning turn
        if use_claude:
            try:
                from config import settings
                from runtime import _client

                client = _client()
                if client and settings.anthropic_api_key:
                    resp = client.messages.create(
                        model=settings.claude_model,
                        max_tokens=120,
                        messages=[
                            {
                                "role": "user",
                                "content": (
                                    f"Mission brief: {mission.brief}\n"
                                    "List 3 short search queries (one per line). No preamble."
                                ),
                            }
                        ],
                    )
                    inp = getattr(resp.usage, "input_tokens", 0) or 0
                    out = getattr(resp.usage, "output_tokens", 0) or 0
                    charge(
                        mission,
                        agent="research",
                        tool="claude_turn",
                        meta={"input_tokens": inp, "output_tokens": out},
                    )
                    mission.log.append(f"claude plan tokens in={inp} out={out}")
            except BudgetDenied:
                raise
            except Exception as e:  # noqa: BLE001
                mission.log.append(f"claude skip: {e}")

        # Research
        metered_web_search(mission, agent="research", query=mission.brief[:80] or "market overview")
        metered_web_search(mission, agent="research", query=f"{mission.client} competitors")

        # Extract from first evidence refs
        refs = [e.url_or_ref for e in mission.evidence if e.url_or_ref][:2]
        for ref in refs:
            metered_extract_facts(mission, agent="extract", source_ref=ref)

        # Verify top claims
        for e in list(mission.evidence)[:3]:
            metered_verify_claim(mission, agent="verify", claim=e.claim)

        metered_compose_report(mission, agent="verify")

        # Prove hard limit: keep searching until deny (or skip if disabled)
        if force_overspend_probe and mission.status == "running":
            try:
                while mission.budget.remaining_cents >= 25:
                    metered_web_search(
                        mission,
                        agent="research",
                        query=f"extra probe {mission.budget.remaining_cents}",
                    )
                # One more that must fail
                metered_web_search(mission, agent="research", query="OVER_BUDGET_PROBE")
            except BudgetDenied as e:
                mission.log.append(f"OVERSPEND PROBE OK: {e}")
                # Hold for human expand/stop
                if sow and mission.work_item_ids:
                    from sow.models import AI_CASHIER

                    wid = mission.work_item_ids[0]
                    try:
                        sow.hold(
                            wid,
                            AI_CASHIER,
                            f"Mission tool budget exhausted — expand or stop ({mission.id})",
                        )
                    except Exception:  # noqa: BLE001
                        pass

    except BudgetDenied as e:
        mission.log.append(f"STOPPED by budget: {e}")
        mission.status = "held"

    # Package deliverable (compose may have been denied — still build from evidence)
    try:
        if not any(c.tool == "compose_report" and c.allowed for c in mission.charges):
            # try once more if budget allows
            try:
                metered_compose_report(mission, agent="verify")
            except BudgetDenied:
                pass
    except Exception:  # noqa: BLE001
        pass

    mission.deliverable_md = build_deliverable(mission)
    if mission.status == "running":
        mission.status = "completed"
    mission.updated_at = now_iso()
    MISSIONS.upsert(mission)

    # Post completion into ERP/NetSuite when completed (not when held)
    posted = None
    if mission.status == "completed" and sow is not None:
        posted = _post_mission_to_sor(mission, sow)

    return {
        "ok": mission.status in {"completed", "held"},
        "mission": mission.to_dict(),
        "job_ledger": mission.job_ledger(),
        "posted": posted,
    }


def complete_after_expand(mission: Mission, *, sow: Any | None = None) -> dict[str, Any]:
    """After human expands budget, finish packaging without another overspend probe."""
    if mission.status == "held":
        mission.status = "running"
    try:
        metered_compose_report(mission, agent="verify")
    except BudgetDenied:
        pass
    mission.deliverable_md = build_deliverable(mission)
    mission.status = "completed"
    mission.log.append("COMPLETED after budget expand")
    MISSIONS.upsert(mission)
    posted = _post_mission_to_sor(mission, sow) if sow else None
    return {"ok": True, "mission": mission.to_dict(), "job_ledger": mission.job_ledger(), "posted": posted}


def _post_mission_to_sor(mission: Mission, sow: Any) -> dict[str, Any] | None:
    from sow.models import AI_CFO, MAYA, SYNC

    try:

        item = sow.create_work(
            SYNC,
            kind="mission_deliverable",  # type: ignore[arg-type]
            subject=mission.id,
            title=f"Job ledger {mission.client} margin ${(mission.quote_cents - mission.budget.spent_cents)/100:.2f}",
            amount_cents=mission.budget.spent_cents,
            evidence=mission.work_item_ids,
            payload={
                "mission_id": mission.id,
                "quote_cents": mission.quote_cents,
                "spent_cents": mission.budget.spent_cents,
                "margin_cents": mission.quote_cents - mission.budget.spent_cents,
                "client": mission.client,
            },
        )
        sow.propose(item.id, AI_CFO, patch={}, reason="mission package ready for owner")
        sow.approve(item.id, MAYA, "accept job ledger")
        sow.post(item.id, destination="netsuite")
        mission.work_item_ids.append(item.id)
    except Exception as e:  # noqa: BLE001
        log.warning("mission deliverable SoW failed: %s", e)
        item = None

    # Direct NetSuite job-cost JE + client party
    try:
        from erp.models import Party
        from erp.netsuite.adapter import NETSUITE
        from erp.store import ERP

        ERP.upsert_party(
            Party(
                id=f"client-{mission.client.lower().replace(' ', '-')[:40]}",
                name=mission.client,
                role="customer",
                tier=1,
                amount_cents=mission.quote_cents,
                meta={"mission_id": mission.id},
            )
        )
        je = NETSUITE.post_journal(
            memo=f"Mission job cost {mission.id}",
            work_item_id=mission.id,
            lines=[
                {"account": "6100", "debit_cents": mission.budget.spent_cents, "credit_cents": 0},
                {"account": "1000", "debit_cents": 0, "credit_cents": mission.budget.spent_cents},
            ],
        )
        NETSUITE.save()
        ERP.save()
        return {"journal_entry": je.get("id"), "client": mission.client}
    except Exception as e:  # noqa: BLE001
        log.warning("mission SoR post failed: %s", e)
        return {"error": str(e)}
