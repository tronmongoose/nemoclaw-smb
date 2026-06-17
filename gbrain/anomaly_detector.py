"""
Per-vendor spend anomaly detection for nemoclaw-smb gbrain.

Exports: Anomaly, score_invoice, scan, build_nemotron_prompt.

Z-score approach mirrors granite_categorize.py detect_anomalies block
(bjornswarm/pipelines/granite_categorize.py:241-266), adapted for
per-vendor invoice history rather than per-category rolling amounts.
"""

import statistics
from collections import defaultdict
from dataclasses import dataclass

# A statistically-outlying invoice is only a business anomaly if it also moves
# the spend a material amount; this floor suppresses z-score false positives on
# tight, small early samples (e.g. a +0.7% wobble that is 2+ std on 3 points).
MIN_PCT_CHANGE = 8.0


@dataclass
class Anomaly:
    """Result of scoring one invoice against its vendor's history."""

    vendor: str
    current_amount: float
    baseline_mean: float
    z_score: float
    pct_change: float
    is_anomaly: bool
    reason: str


def score_invoice(
    vendor: str,
    amount: float,
    history: list[float],
    z_threshold: float = 2.0,
) -> Anomaly:
    """Score a single invoice against the vendor's prior history.

    Returns is_anomaly=False with reason 'insufficient history' when
    fewer than 2 history points exist (skip beats fabricate).
    Handles std_dev==0 by setting z_score=0.
    """
    if len(history) < 2:
        return Anomaly(
            vendor=vendor,
            current_amount=amount,
            baseline_mean=float(history[0]) if history else 0.0,
            z_score=0.0,
            pct_change=0.0,
            is_anomaly=False,
            reason="insufficient history",
        )

    mean = statistics.mean(history)
    std_dev = statistics.pstdev(history)  # population std-dev; history IS the population

    z_score = (amount - mean) / std_dev if std_dev > 0 else 0.0
    pct_change = ((amount - mean) / mean * 100) if mean != 0 else 0.0
    is_anomaly = abs(z_score) > z_threshold and abs(pct_change) >= MIN_PCT_CHANGE

    if is_anomaly:
        direction = "up" if pct_change >= 0 else "down"
        reason = (
            f"{direction} {abs(pct_change):.0f}% from "
            f"${mean:.0f} to ${amount:.0f} "
            f"(z={z_score:.2f})"
        )
    else:
        reason = "within normal range"

    return Anomaly(
        vendor=vendor,
        current_amount=amount,
        baseline_mean=round(mean, 2),
        z_score=round(z_score, 2),
        pct_change=round(pct_change, 1),
        is_anomaly=is_anomaly,
        reason=reason,
    )


def scan(invoices: list[dict], z_threshold: float = 2.0) -> list[Anomaly]:
    """Group invoices by vendor (date order) and score each against prior history.

    Each invoice dict must have keys: vendor (str), amount (float), date (str).
    Returns only anomalies (is_anomaly=True), sorted descending by abs z-score.

    #COMPLETION_DRIVE: invoices are pre-sorted or sortable by the 'date' key as a str (ISO 8601).
    """
    by_vendor: dict[str, list[dict]] = defaultdict(list)
    for inv in invoices:
        by_vendor[inv["vendor"]].append(inv)

    for vendor in by_vendor:
        by_vendor[vendor].sort(key=lambda x: x["date"])

    anomalies: list[Anomaly] = []
    for vendor, vendor_invoices in by_vendor.items():
        history: list[float] = []
        for inv in vendor_invoices:
            result = score_invoice(vendor, inv["amount"], history, z_threshold)
            if result.is_anomaly:
                anomalies.append(result)
            history.append(inv["amount"])

    anomalies.sort(key=lambda a: abs(a.z_score), reverse=True)
    return anomalies


def build_nemotron_prompt(anomaly: Anomaly, context: dict) -> str:
    """Compose a Nemotron 3 Ultra prompt to reason over a flagged anomaly.

    The prompt instructs the model to treat the provided context as the ONLY
    valid source (no prior/training knowledge) and to return 'skip' if context
    is too thin to support a conclusion.

    Does NOT call any LLM. Returns the prompt string only.
    """
    ctx_lines = "\n".join(f"  {k}: {v}" for k, v in context.items())
    return (
        "You are a financial reasoning assistant. "
        "Use ONLY the structured data provided below as your source of truth. "
        "Do not draw on any prior knowledge or training data. "
        "If the context is too thin to support a conclusion, return exactly: skip\n\n"
        "## Flagged Invoice Anomaly\n"
        f"  vendor: {anomaly.vendor}\n"
        f"  current_amount: ${anomaly.current_amount:.2f}\n"
        f"  baseline_mean: ${anomaly.baseline_mean:.2f}\n"
        f"  z_score: {anomaly.z_score}\n"
        f"  pct_change: {anomaly.pct_change:+.1f}%\n"
        f"  reason: {anomaly.reason}\n\n"
        "## Additional Context\n"
        f"{ctx_lines}\n\n"
        "## Task\n"
        "1. Identify the most likely root cause of this spend anomaly.\n"
        "2. Provide a concrete recommendation (approve, escalate, investigate, reject).\n"
        "3. State your confidence (high / medium / low) and why.\n"
        "Return your answer in plain text. If context is insufficient, return: skip"
    )
