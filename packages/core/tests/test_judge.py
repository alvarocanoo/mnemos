from unittest.mock import MagicMock

import pytest

from mnemos.contradiction.judge import (
    ContradictionJudge,
    JudgeUnavailableError,
)
from mnemos.contradiction.types import ContradictionInput, Verdict


def test_judge_without_api_key_raises_when_called(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    judge = ContradictionJudge(api_key=None)
    assert judge.available is False
    with pytest.raises(JudgeUnavailableError):
        judge.judge(ContradictionInput(memory_a="x", memory_b="y"))


def _fake_response(verdict: str, reason: str = "stub reason"):
    block = MagicMock()
    block.type = "tool_use"
    block.name = "report_verdict"
    block.input = {"verdict": verdict, "reason": reason}
    response = MagicMock()
    response.content = [block]
    return response


def test_judge_parses_tool_use_block():
    judge = ContradictionJudge(api_key="sk-fake")
    judge._client = MagicMock()
    judge._client.messages.create.return_value = _fake_response("contradicts", "A and B disagree")

    result = judge.judge(ContradictionInput(memory_a="A", memory_b="B"))
    assert result.verdict is Verdict.CONTRADICTS
    assert "disagree" in result.reason
    assert result.judge_model == judge.model


def test_judge_raises_when_no_tool_use_block():
    judge = ContradictionJudge(api_key="sk-fake")
    judge._client = MagicMock()
    bad_block = MagicMock()
    bad_block.type = "text"
    bad_response = MagicMock()
    bad_response.content = [bad_block]
    judge._client.messages.create.return_value = bad_response

    with pytest.raises(RuntimeError, match="tool_use"):
        judge.judge(ContradictionInput(memory_a="A", memory_b="B"))


def test_judge_passes_model_to_create():
    judge = ContradictionJudge(model="claude-sonnet-4-6", api_key="sk-fake", max_tokens=128)
    judge._client = MagicMock()
    judge._client.messages.create.return_value = _fake_response("paraphrase")

    judge.judge(ContradictionInput(memory_a="hello", memory_b="hi"))

    call_kwargs = judge._client.messages.create.call_args.kwargs
    assert call_kwargs["model"] == "claude-sonnet-4-6"
    assert call_kwargs["max_tokens"] == 128
    assert call_kwargs["tool_choice"]["name"] == "report_verdict"
