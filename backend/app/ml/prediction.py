"""Abstain-and-refer decision policy.

Three bands:

* ``REFER``          predictive entropy > refer threshold, or the input failed a
                     quality guard. No automatic decision is produced.
* ``AUTO-POSITIVE``  confident pneumonia prediction. Always queued for
                     mandatory human review (oversight design).
* ``AUTO-NEGATIVE``  confident normal prediction.

The policy parameters are read from the versioned model configuration; they
are never changed at runtime.
"""
from __future__ import annotations

from dataclasses import dataclass

AUTO_NEGATIVE = "AUTO-NEGATIVE"
AUTO_POSITIVE = "AUTO-POSITIVE"
REFER = "REFER"
BANDS = (AUTO_NEGATIVE, AUTO_POSITIVE, REFER)


@dataclass(frozen=True)
class DecisionPolicy:
    refer_threshold: float
    decision_threshold: float = 0.5
    refer_on_input_flags: bool = True

    def __post_init__(self):
        if not 0 < self.refer_threshold <= 1:
            raise ValueError("refer_threshold must be in (0, 1] bits")
        if not 0 < self.decision_threshold < 1:
            raise ValueError("decision_threshold must be in (0, 1)")


@dataclass(frozen=True)
class Decision:
    band: str
    predicted_class: str
    requires_review: bool
    reason: str


def decide(p_pneumonia: float, predictive_entropy: float, policy: DecisionPolicy,
           blocking_flags: list[str] | None = None) -> Decision:
    predicted = "PNEUMONIA" if p_pneumonia >= policy.decision_threshold else "NORMAL"
    if blocking_flags and policy.refer_on_input_flags:
        return Decision(REFER, predicted, True,
                        "Input quality guard: " + "; ".join(blocking_flags) + ". No automatic decision issued.")
    if predictive_entropy > policy.refer_threshold:
        return Decision(REFER, predicted, True,
                        f"Predictive entropy {predictive_entropy:.3f} bits exceeds the refer threshold "
                        f"{policy.refer_threshold:.3f}. No automatic decision issued.")
    if predicted == "PNEUMONIA":
        return Decision(AUTO_POSITIVE, predicted, True,
                        "Confident positive prediction. Mandatory human review per oversight design.")
    return Decision(AUTO_NEGATIVE, predicted, False,
                    "Confident negative prediction within the uncertainty threshold.")
