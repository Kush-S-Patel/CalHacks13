"""Metered research / extract / verify tools — every call hits BudgetController."""

from __future__ import annotations

from typing import Any

from missions.budget import BudgetDenied, charge
from missions.models import EvidenceItem, Mission, new_id

# Stub corpus for offline / deterministic demo (no paid search required)
STUB_SOURCES: list[dict[str, str]] = [
    {
        "title": "Acme Corp Q3 product roadmap notes",
        "url": "stub://acme/roadmap-q3",
        "snippet": "Acme prioritizes warehouse automation and two regional pilots in CA/NV.",
    },
    {
        "title": "Industry wage band survey 2026",
        "url": "stub://labor/wage-bands-2026",
        "snippet": "Mid-market ops analysts: $78k–$92k base; contractors $65–$85/hr.",
    },
    {
        "title": "Competitor Coastal Grain press release",
        "url": "stub://news/coastal-grain",
        "snippet": "Coastal Grain Alt expands West Coast distribution; flour spot +12% YoY.",
    },
    {
        "title": "Local chamber workforce brief",
        "url": "stub://chamber/workforce",
        "snippet": "Berkeley/Oakland food manufacturing hiring steady; retention risk on night shift.",
    },
]


def metered_web_search(mission: Mission, *, agent: str, query: str) -> dict[str, Any]:
    charge(mission, agent=agent, tool="web_search", meta={"query": query})
    q = query.lower()
    hits = [s for s in STUB_SOURCES if any(tok in (s["title"] + s["snippet"]).lower() for tok in q.split()[:4])]
    if not hits:
        hits = STUB_SOURCES[:2]
    for h in hits:
        mission.evidence.append(
            EvidenceItem(
                id=new_id("ev"),
                source=h["title"],
                claim=h["snippet"],
                confidence=0.7,
                agent=agent,
                url_or_ref=h["url"],
            )
        )
    return {"ok": True, "query": query, "hits": hits, "count": len(hits)}


def metered_extract_facts(mission: Mission, *, agent: str, source_ref: str) -> dict[str, Any]:
    charge(mission, agent=agent, tool="extract_facts", meta={"source_ref": source_ref})
    src = next((s for s in STUB_SOURCES if s["url"] == source_ref or source_ref in s["title"]), STUB_SOURCES[0])
    facts = [
        f"Fact from {src['title']}: {src['snippet']}",
        f"Source ref: {src['url']}",
    ]
    for f in facts:
        mission.evidence.append(
            EvidenceItem(
                id=new_id("ev"),
                source=src["title"],
                claim=f,
                confidence=0.8,
                agent=agent,
                url_or_ref=src["url"],
            )
        )
    return {"ok": True, "facts": facts, "source": src}


def metered_verify_claim(mission: Mission, *, agent: str, claim: str) -> dict[str, Any]:
    charge(mission, agent=agent, tool="verify_claim", meta={"claim": claim[:200]})
    # Deterministic check: claim must echo something already in evidence
    support = [e for e in mission.evidence if any(w in e.claim.lower() for w in claim.lower().split()[:3] if len(w) > 3)]
    ok = len(support) >= 1
    for e in support[:3]:
        e.verified = ok
        e.notes = "cross-checked by verify agent" if ok else "unsupported"
    if not ok:
        mission.exceptions.append(f"Unverified claim: {claim[:120]}")
    return {"ok": ok, "support_count": len(support), "claim": claim}


def metered_compose_report(mission: Mission, *, agent: str) -> dict[str, Any]:
    charge(mission, agent=agent, tool="compose_report")
    return {"ok": True}


# Re-export for callers that catch denials
__all__ = [
    "BudgetDenied",
    "metered_web_search",
    "metered_extract_facts",
    "metered_verify_claim",
    "metered_compose_report",
    "STUB_SOURCES",
]
