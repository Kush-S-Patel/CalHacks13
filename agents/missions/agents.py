"""Mission agent prompts + tool schemas (research / extract / verify)."""

from __future__ import annotations

MISSION_PROMPTS: dict[str, str] = {
    "research": """You are the Research agent on a budgeted client mission.
Find sources relevant to the brief. Prefer tool web_search.
You cannot exceed the mission tool budget — denials are enforced in code.
Do not invent URLs; use tools.""",
    "extract": """You are the Extraction agent.
Pull structured facts from approved source refs via extract_facts.
Stay within mission budget. Cite source_ref from prior research.""",
    "verify": """You are the Verification agent.
Check claims against evidence via verify_claim. Flag unsupported claims.
Do not spend past the mission budget.""",
}

MISSION_TOOLS: dict[str, list[dict]] = {
    "research": [
        {
            "name": "web_search",
            "description": "Metered web search within mission budget. Returns stub/live hits.",
            "input_schema": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        }
    ],
    "extract": [
        {
            "name": "extract_facts",
            "description": "Metered extraction from a source_ref discovered by research.",
            "input_schema": {
                "type": "object",
                "properties": {"source_ref": {"type": "string"}},
                "required": ["source_ref"],
            },
        }
    ],
    "verify": [
        {
            "name": "verify_claim",
            "description": "Metered verification of a claim against mission evidence.",
            "input_schema": {
                "type": "object",
                "properties": {"claim": {"type": "string"}},
                "required": ["claim"],
            },
        }
    ],
}
