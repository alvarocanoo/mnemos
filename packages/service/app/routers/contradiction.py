from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from functools import lru_cache

from mnemos.config import Settings
from mnemos.contradiction.judge import (
    ContradictionJudge,
    JudgeUnavailableError,
)
from mnemos.contradiction.nli import NLIBaseline, NLIUnavailableError
from mnemos.contradiction.types import ContradictionInput, ContradictionResult
from mnemos.memory.ops import read_memory_by_id

from app.deps import SessionDep, SettingsDep

router = APIRouter(prefix="/contradiction", tags=["contradiction"])


class DetectByText(BaseModel):
    memory_a: str = Field(..., min_length=1, max_length=8000)
    memory_b: str = Field(..., min_length=1, max_length=8000)


class DetectByIds(BaseModel):
    memory_a_id: UUID
    memory_b_id: UUID


def _judge(settings: Settings) -> ContradictionJudge:
    return ContradictionJudge(
        model=settings.judge_model,
        api_key=settings.anthropic_api_key,
        max_tokens=settings.judge_max_tokens,
    )


@lru_cache(maxsize=1)
def _nli_singleton(model_name: str, threshold: float) -> NLIBaseline:
    return NLIBaseline(model_name=model_name, threshold=threshold)


def _baseline(settings: Settings) -> NLIBaseline:
    return _nli_singleton(settings.nli_model, settings.nli_threshold)


def _call_judge(judge: ContradictionJudge, payload: ContradictionInput) -> ContradictionResult:
    try:
        return judge.judge(payload)
    except JudgeUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


def _call_baseline(baseline: NLIBaseline, payload: ContradictionInput) -> ContradictionResult:
    try:
        return baseline.judge(payload)
    except NLIUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


@router.post("/detect", response_model=ContradictionResult)
def detect_by_text(
    payload: DetectByText,
    settings: Settings = SettingsDep,
) -> ContradictionResult:
    return _call_judge(
        _judge(settings),
        ContradictionInput(memory_a=payload.memory_a, memory_b=payload.memory_b),
    )


@router.post("/detect-by-ids", response_model=ContradictionResult)
def detect_by_ids(
    payload: DetectByIds,
    session: Session = SessionDep,
    settings: Settings = SettingsDep,
) -> ContradictionResult:
    a = read_memory_by_id(session, payload.memory_a_id, bump_access=False)
    b = read_memory_by_id(session, payload.memory_b_id, bump_access=False)
    if a is None or b is None:
        raise HTTPException(status_code=404, detail="memory not found")
    return _call_judge(
        _judge(settings),
        ContradictionInput(memory_a=a.content, memory_b=b.content),
    )


@router.post("/baseline", response_model=ContradictionResult)
def detect_baseline(
    payload: DetectByText,
    settings: Settings = SettingsDep,
) -> ContradictionResult:
    """NLI baseline (cross-encoder/nli-deberta-v3-base, bidirectional).

    No API key needed; runs entirely locally. Used to report the gap
    between a small specialized classifier and the LLM judge.
    """
    return _call_baseline(
        _baseline(settings),
        ContradictionInput(memory_a=payload.memory_a, memory_b=payload.memory_b),
    )
