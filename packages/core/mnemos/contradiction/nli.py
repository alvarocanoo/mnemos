from __future__ import annotations

from typing import Any

from mnemos.contradiction.types import (
    ContradictionInput,
    ContradictionResult,
    Verdict,
)

_DEFAULT_MODEL = "cross-encoder/nli-deberta-v3-base"

_REQUIRED_LABELS = {"contradiction", "entailment", "neutral"}


class NLIUnavailableError(RuntimeError):
    """Raised when the NLI baseline cannot be used."""


class NLIBaseline:
    """NLI-based contradiction classifier, bidirectional.

    Why this exists: it is the apples-to-something comparison for the LLM
    judge. Reporting both side by side is the contribution — we measure
    the gap between a small specialized classifier and a frontier LLM.

    Mapping NLI -> mnemos Verdict (documented limitations):
        contradiction (either direction above threshold)  -> CONTRADICTS
        entailment (both directions above threshold)       -> PARAPHRASE
        otherwise (neutral dominates)                      -> INDEPENDENT
        SUPERSEDES is not expressible in symmetric NLI; the baseline
        cannot distinguish it from CONTRADICTS. We fall back to
        CONTRADICTS and document the gap rather than fake it.
    """

    def __init__(
        self,
        model_name: str = _DEFAULT_MODEL,
        threshold: float = 0.5,
    ) -> None:
        self.model_name = model_name
        self.threshold = threshold
        self._tokenizer: Any | None = None
        self._model: Any | None = None
        self._labels_lower: list[str] | None = None

    @property
    def available(self) -> bool:
        try:
            import torch  # noqa: F401
            import transformers  # noqa: F401
        except ImportError:
            return False
        return True

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        try:
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
        except ImportError as exc:
            raise NLIUnavailableError(
                "transformers/torch not installed in this environment."
            ) from exc

        self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self._model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
        self._model.eval()

        id2label = getattr(self._model.config, "id2label", None)
        if not id2label:
            raise NLIUnavailableError(
                f"Model {self.model_name} has no id2label in config; cannot map outputs."
            )
        labels = [str(id2label[i]).lower() for i in range(len(id2label))]
        missing = _REQUIRED_LABELS - set(labels)
        if missing:
            raise NLIUnavailableError(
                f"Model {self.model_name} labels are {labels}; missing {sorted(missing)}."
            )
        self._labels_lower = labels

    def _nli_probs(self, premise: str, hypothesis: str) -> dict[str, float]:
        import torch

        assert self._tokenizer is not None and self._model is not None
        assert self._labels_lower is not None

        inputs = self._tokenizer(
            premise,
            hypothesis,
            return_tensors="pt",
            truncation=True,
            max_length=512,
        )
        with torch.no_grad():
            logits = self._model(**inputs).logits
        probs = torch.softmax(logits[0], dim=-1).tolist()
        return dict(zip(self._labels_lower, probs, strict=True))

    def judge(self, payload: ContradictionInput) -> ContradictionResult:
        if not self.available:
            raise NLIUnavailableError("transformers + torch not installed.")
        self._ensure_loaded()

        a_to_b = self._nli_probs(payload.memory_a, payload.memory_b)
        b_to_a = self._nli_probs(payload.memory_b, payload.memory_a)

        contra = max(a_to_b["contradiction"], b_to_a["contradiction"])
        entail = min(a_to_b["entailment"], b_to_a["entailment"])

        if contra > self.threshold:
            verdict = Verdict.CONTRADICTS
            reason = (
                f"NLI contradiction max={contra:.3f} "
                f"(A->B={a_to_b['contradiction']:.3f}, "
                f"B->A={b_to_a['contradiction']:.3f}); "
                f"SUPERSEDES not distinguishable in symmetric NLI."
            )
        elif entail > self.threshold:
            verdict = Verdict.PARAPHRASE
            reason = (
                f"NLI bidirectional entailment min={entail:.3f} "
                f"(A->B={a_to_b['entailment']:.3f}, "
                f"B->A={b_to_a['entailment']:.3f})"
            )
        else:
            verdict = Verdict.INDEPENDENT
            reason = (
                f"NLI: neither contradiction nor entailment "
                f"above threshold {self.threshold} "
                f"(contra_max={contra:.3f}, entail_min={entail:.3f})"
            )

        return ContradictionResult(verdict=verdict, reason=reason, judge_model=self.model_name)
