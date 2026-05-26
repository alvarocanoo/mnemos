from __future__ import annotations

import os
from typing import Any

import anthropic

from mnemos.contradiction.types import ContradictionInput, ContradictionResult, Verdict


_TOOL_NAME = "report_verdict"

_TOOL_SCHEMA: dict[str, Any] = {
    "name": _TOOL_NAME,
    "description": (
        "Report whether two stored memories conflict, supersede each other, "
        "are unrelated, or say the same thing in different words."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "verdict": {
                "type": "string",
                "enum": [v.value for v in Verdict],
                "description": (
                    "contradicts: both cannot be true at the same time. "
                    "supersedes: memory B replaces/updates memory A "
                    "(B is the newer/corrected version of the same fact). "
                    "independent: A and B are about unrelated things. "
                    "paraphrase: A and B express the same fact in different words."
                ),
            },
            "reason": {
                "type": "string",
                "description": "One short sentence justifying the verdict.",
                "maxLength": 300,
            },
        },
        "required": ["verdict", "reason"],
    },
}

_SYSTEM_PROMPT = (
    "You are a precise classifier for an agent memory system. "
    "You decide how two stored memories relate to each other. "
    "Always call the report_verdict tool. Do not output free text."
)

_USER_TEMPLATE = (
    "Memory A:\n{a}\n\n"
    "Memory B:\n{b}\n\n"
    "Classify the relationship between A and B using the report_verdict tool."
)


class JudgeUnavailableError(RuntimeError):
    """Raised when the LLM judge cannot be used (no API key, no client)."""


class ContradictionJudge:
    """LLM-as-judge classifier for memory contradiction.

    Calls Claude with a forced tool_use so the output is always a structured
    {verdict, reason} object — no free-form parsing.
    """

    def __init__(
        self,
        model: str = "claude-haiku-4-5",
        *,
        api_key: str | None = None,
        max_tokens: int = 256,
    ) -> None:
        self.model = model
        self.max_tokens = max_tokens
        resolved_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not resolved_key:
            self._client: anthropic.Anthropic | None = None
        else:
            self._client = anthropic.Anthropic(api_key=resolved_key)

    @property
    def available(self) -> bool:
        return self._client is not None

    def judge(self, payload: ContradictionInput) -> ContradictionResult:
        if self._client is None:
            raise JudgeUnavailableError(
                "No ANTHROPIC_API_KEY configured. Set it in env or pass api_key."
            )

        response = self._client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=_SYSTEM_PROMPT,
            tools=[_TOOL_SCHEMA],
            tool_choice={"type": "tool", "name": _TOOL_NAME},
            messages=[
                {
                    "role": "user",
                    "content": _USER_TEMPLATE.format(
                        a=payload.memory_a, b=payload.memory_b
                    ),
                }
            ],
        )

        for block in response.content:
            if getattr(block, "type", None) == "tool_use" and block.name == _TOOL_NAME:
                data = block.input
                return ContradictionResult(
                    verdict=Verdict(data["verdict"]),
                    reason=str(data.get("reason", "")),
                    judge_model=self.model,
                )

        raise RuntimeError(
            f"Judge did not produce a tool_use block; got: {response.content!r}"
        )
