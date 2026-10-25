"""Fail-closed Claude adapter for interpreting reimbursement claim rules.

The model may explain a rule, but it may not invent the evidence for that rule.
Every successful interpretation is tied to a literal quote from the retrieved
document and to the caller-provided source URL.
"""

from __future__ import annotations

import logging
from typing import Any

from anthropic import Anthropic
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictStr, ValidationError, model_validator

from config import settings

log = logging.getLogger("swarmcfo.claims.rule_interpreter")


class RuleInterpretation(BaseModel):
    """The only shape accepted from Claude for a claim-rule decision."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    rule: StrictStr = Field(min_length=1)
    exact_quote: StrictStr = Field(min_length=1)
    source_url: StrictStr = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    needs_human: StrictBool
    suggested_question: StrictStr

    @model_validator(mode="after")
    def require_question_for_human_review(self) -> "RuleInterpretation":
        if self.needs_human and not self.suggested_question.strip():
            raise ValueError("suggested_question must be non-empty when needs_human is true")
        return self


class RuleInterpretationError(RuntimeError):
    """A safe-stop signal: no automated claim decision should be made."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


_TOOL_NAME = "submit_claim_rule_interpretation"

RULE_INTERPRETATION_TOOL: dict[str, Any] = {
    "name": _TOOL_NAME,
    "description": (
        "Submit one evidence-backed interpretation of a reimbursement claim rule. "
        "The exact_quote must be copied character-for-character from RETRIEVED CLEAN TEXT."
    ),
    "input_schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "rule": {
                "type": "string",
                "minLength": 1,
                "description": "Plain-language rule that applies to the claim review question.",
            },
            "exact_quote": {
                "type": "string",
                "minLength": 1,
                "description": "Literal supporting quote copied from the retrieved clean text.",
            },
            "source_url": {
                "type": "string",
                "minLength": 1,
                "description": "The supplied trusted source URL, unchanged.",
            },
            "confidence": {
                "type": "number",
                "minimum": 0,
                "maximum": 1,
                "description": "Confidence that the quoted source supports the interpreted rule.",
            },
            "needs_human": {
                "type": "boolean",
                "description": "True when the source is ambiguous or the claim needs judgment.",
            },
            "suggested_question": {
                "type": "string",
                "description": "Specific question for a reviewer; empty only when no review is needed.",
            },
        },
        "required": [
            "rule",
            "exact_quote",
            "source_url",
            "confidence",
            "needs_human",
            "suggested_question",
        ],
    },
}

_SYSTEM_PROMPT = """You interpret grant and reimbursement rules for a nonprofit claim reviewer.

Use only RETRIEVED CLEAN TEXT as evidence. Never rely on memory or outside knowledge.
The exact_quote must be copied character-for-character from that text and must directly
support the rule. Preserve the supplied source URL exactly. If the language is ambiguous,
set needs_human=true and ask one concrete question. Do not make an eligibility decision
when the retrieved source does not support one; in that case, do not fabricate a quote.
Submit exactly one interpretation with the provided tool."""


def _client() -> Anthropic | None:
    """Mirror the shared runtime's credential-gated Anthropic client."""
    if not settings.anthropic_api_key:
        return None
    return Anthropic(api_key=settings.anthropic_api_key)


def _value(block: Any, key: str, default: Any = None) -> Any:
    if isinstance(block, dict):
        return block.get(key, default)
    return getattr(block, key, default)


def _tool_payload(response: Any) -> Any:
    content = _value(response, "content")
    if not isinstance(content, list):
        raise RuleInterpretationError("invalid_response", "Claude response has no content blocks")

    calls = [
        block
        for block in content
        if _value(block, "type") == "tool_use" and _value(block, "name") == _TOOL_NAME
    ]
    if len(calls) != 1:
        raise RuleInterpretationError(
            "invalid_response",
            f"expected exactly one {_TOOL_NAME} tool call, received {len(calls)}",
        )
    return _value(calls[0], "input")


def interpret_claim_rule(
    *,
    review_question: str,
    clean_text: str,
    source_url: str,
    client: Any | None = None,
    model: str | None = None,
) -> RuleInterpretation:
    """Ask Claude for one source-grounded claim rule and verify it locally.

    Raises :class:`RuleInterpretationError` for missing credentials, API errors,
    malformed model output, a changed source URL, or a quote that cannot be found
    literally in ``clean_text``. Callers must treat every such error as a hold for
    human review, never as permission to continue automatically.
    """

    if not isinstance(review_question, str) or not review_question.strip():
        raise RuleInterpretationError("invalid_input", "review_question must be non-empty")
    if not isinstance(clean_text, str) or not clean_text.strip():
        raise RuleInterpretationError("invalid_input", "clean_text must be non-empty")
    if not isinstance(source_url, str) or not source_url.strip():
        raise RuleInterpretationError("invalid_input", "source_url must be non-empty")

    anthropic_client = client if client is not None else _client()
    if anthropic_client is None:
        raise RuleInterpretationError(
            "claude_unavailable",
            "ANTHROPIC_API_KEY is not configured; send this rule to human review",
        )

    user_message = (
        f"CLAIM REVIEW QUESTION:\n{review_question}\n\n"
        f"TRUSTED SOURCE URL:\n{source_url}\n\n"
        f"RETRIEVED CLEAN TEXT:\n<source>\n{clean_text}\n</source>"
    )
    try:
        response = anthropic_client.messages.create(
            model=model or settings.claude_model,
            max_tokens=768,
            system=_SYSTEM_PROMPT,
            tools=[RULE_INTERPRETATION_TOOL],
            tool_choice={"type": "tool", "name": _TOOL_NAME},
            messages=[{"role": "user", "content": user_message}],
        )
    except Exception as exc:  # noqa: BLE001 - convert SDK failures to a safe stop
        log.exception("claim rule interpretation call failed")
        raise RuleInterpretationError(
            "claude_call_failed",
            "Claude rule interpretation failed; send this rule to human review",
        ) from exc

    payload = _tool_payload(response)
    try:
        interpretation = RuleInterpretation.model_validate(payload, strict=True)
    except ValidationError as exc:
        raise RuleInterpretationError(
            "invalid_schema",
            "Claude returned an invalid claim-rule schema; send this rule to human review",
        ) from exc

    if interpretation.source_url != source_url:
        raise RuleInterpretationError(
            "source_mismatch",
            "Claude changed the trusted source URL; send this rule to human review",
        )
    if interpretation.exact_quote not in clean_text:
        raise RuleInterpretationError(
            "unverifiable_quote",
            "Claude's quote was not found literally in retrieved clean_text; send this rule to human review",
        )

    return interpretation
