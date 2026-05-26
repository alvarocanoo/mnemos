from enum import StrEnum

from pydantic import BaseModel, Field


class Verdict(StrEnum):
    CONTRADICTS = "contradicts"
    SUPERSEDES = "supersedes"
    INDEPENDENT = "independent"
    PARAPHRASE = "paraphrase"


POSITIVE_VERDICTS: frozenset[Verdict] = frozenset(
    {Verdict.CONTRADICTS, Verdict.SUPERSEDES}
)


class ContradictionInput(BaseModel):
    memory_a: str = Field(..., min_length=1, max_length=8000)
    memory_b: str = Field(..., min_length=1, max_length=8000)


class ContradictionResult(BaseModel):
    verdict: Verdict
    reason: str
    judge_model: str
