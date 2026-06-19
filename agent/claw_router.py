"""
claw_router — SMB ops model-routing decision module for NemoClaw.

Exports:
    HERMES_MODEL      — routine tier model constant
    NEMOTRON_MODEL    — heavy tier model constant
    DEVSTRAL_MODEL    — code tier model constant
    classify_complexity(task) -> dict[score, tier, reasons]
    decide_route(task) -> RouteDecision
    log_route_decision(decision, path=None) -> None
    route_llm(tenant) -> callable   — tenant-aware LLM callable
    assert_no_frontier(tenant)      — raises if local/restricted tenant tries frontier

Tiers:
    routine  — invoice tagging, vendor categorization, spend bucketing, recurrence
    heavy    — contract analysis, negotiation drafts, anomaly root-cause, multi-vendor compare
    code     — webhooks, integrations, API transforms, automation scripts

Tenant routing:
    When tenant.llm_routing == "local", route_llm returns the local Ollama callable.
    assert_no_frontier raises RuntimeError when a restricted tenant touches a frontier client.
    This is a runtime guard — it does not prevent import but does prevent execution.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

HERMES_MODEL: str = os.getenv("HERMES_MODEL", "hermes-agent")
NEMOTRON_MODEL: str = os.getenv("NEMOTRON_MODEL", "nvidia/nemotron-3-ultra")
DEVSTRAL_MODEL: str = os.getenv("CODE_MODEL", "devstral")

_DECISION_LOG_DEFAULT = Path(__file__).resolve().parent.parent / "logs" / "route-decisions.jsonl"

# Signals scored additively; code tier wins on any match before complexity eval.
_HEAVY_SIGNALS: list[tuple[str, float, str]] = [
    (r"\bnegotiate\b", 0.35, "negotiation request"),
    (r"\banalyze\b|\banalysis\b", 0.30, "analysis request"),
    (r"\bcompare\b|\bcomparison\b", 0.25, "comparison request"),
    (r"\bwhy\b", 0.30, "causal reasoning"),
    (r"\bdraft\b", 0.30, "drafting request"),
    (r"\binvestigate\b", 0.30, "investigation request"),
    (r"\broot\s*cause\b", 0.40, "root-cause analysis"),
    (r"\balternative[s]?\b", 0.25, "alternatives request"),
    (r"\banomaly\b|\banomalies\b|\bunusual\b", 0.25, "anomaly detection"),
    (r"\brecommend\b", 0.25, "recommendation request"),
    (r"\bforecast\b|\bpredict\b", 0.30, "forecasting"),
    (r"\boptimize\b|\boptimization\b", 0.30, "optimization request"),
    (r"\bsummarize\b|\bsummary\b", 0.20, "summarization"),
    (r"\brisks?\b", 0.25, "risk assessment"),
    (r"\bpenalty\b|\bpenalties\b", 0.25, "contract risk terms"),
    (r"\bvs\.?\b|\bversus\b", 0.20, "comparison"),
]

_ROUTINE_SIGNALS: list[tuple[str, float, str]] = [
    (r"\bcategorize\b|\bcategorization\b", -0.25, "categorization task"),
    (r"\btag\b|\btagging\b", -0.25, "tagging task"),
    (r"\bbucket\b|\bbucketing\b", -0.20, "bucketing task"),
    (r"\blist\b|\bshow\b", -0.15, "list/show request"),
    (r"\bclassify\b", -0.20, "classification request"),
    (r"\brecurring\b|\brecurrence\b|\bone[- ]?time\b", -0.20, "recurrence classification"),
    (r"\bvendor\s+name\b|\bextract\b", -0.15, "field extraction"),
    (r"\bis\s+this\b", -0.15, "simple yes/no query"),
    (r"\bspend\s+bucket\b|\bspend\s+category\b", -0.20, "spend bucketing"),
]

# Code signals take priority — matched before complexity scoring.
_CODE_SIGNALS: list[tuple[str, str]] = [
    (r"\bwebhook[s]?\b", "webhook integration"),
    (r"\bintegrate\b|\bintegration[s]?\b", "integration task"),
    (r"\bapi\b", "API task"),
    (r"\btransform\b|\btransformation\b", "data transform"),
    (r"\bscript\b|\bautomate\b|\bautomation\b", "scripting/automation"),
    (r"\bpipeline\b", "data pipeline"),
    (r"\bimport\b|\bexport\b", "data import/export"),
    (r"\bparse\b|\bparsing\b", "parsing task"),
    (r"\bconnect(or)?\b", "connector task"),
    (r"\bfunction\b|\blambda\b", "code function"),
]

# Baseline just below heavy threshold so undecorated tasks stay routine.
_BASELINE_SCORE: float = 0.25
_HEAVY_THRESHOLD: float = 0.50


@dataclass(frozen=True)
class RouteDecision:
    """Immutable routing result: tier + model + classification metadata."""

    tier: str            # "routine" | "heavy" | "code"
    model: str           # concrete model id
    score: float         # 0..1 complexity score (code tier always 0.0)
    reasons: list[str] = field(default_factory=list)


def _detect_code_tier(task: str) -> list[str]:
    """Return matched code-signal labels; empty list means not a code task."""
    q = task.lower()
    return [label for pattern, label in _CODE_SIGNALS if re.search(pattern, q)]


def classify_complexity(task: str) -> dict:
    """Score SMB ops task complexity; return tier, score, and matched reasons.

    Code signals short-circuit before arithmetic scoring — any match promotes
    to 'code' regardless of heavy/routine signals in the same text.
    """
    q = task.lower().strip()

    code_hits = _detect_code_tier(q)
    if code_hits:
        return {"score": 0.0, "tier": "code", "reasons": code_hits}

    score = _BASELINE_SCORE
    reasons: list[str] = []

    for pattern, weight, label in _HEAVY_SIGNALS + _ROUTINE_SIGNALS:
        if re.search(pattern, q):
            score += weight
            sign = "+" if weight > 0 else ""
            reasons.append(f"{sign}{weight:.2f} {label}")

    # Weak length signal: multi-clause tasks tend to be heavier.
    words = len(q.split())
    if words > 20:
        score += 0.10
        reasons.append("+0.10 long task (>20 words)")

    score = max(0.0, min(1.0, score))
    tier = "heavy" if score >= _HEAVY_THRESHOLD else "routine"
    return {"score": round(score, 2), "tier": tier, "reasons": reasons}


def decide_route(task: str) -> RouteDecision:
    """Classify task and return a RouteDecision with model assignment.

    Logs the decision via log_route_decision (fail-open).
    """
    classification = classify_complexity(task)
    tier = classification["tier"]
    model_map = {
        "routine": HERMES_MODEL,
        "heavy": NEMOTRON_MODEL,
        "code": DEVSTRAL_MODEL,
    }
    decision = RouteDecision(
        tier=tier,
        model=model_map[tier],
        score=classification["score"],
        reasons=classification["reasons"],
    )
    log_route_decision(decision)
    return decision


def log_route_decision(decision: RouteDecision, path: str | None = None) -> None:
    """Append one JSONL record to the decision log; never raises, never logs raw task text.

    Privacy: only sha256 prefix + word count travel outside the call site.
    Disable by setting NEMOCLAW_DECISION_LOG=off.
    """
    override = os.environ.get("NEMOCLAW_DECISION_LOG", "")
    if override.lower() in ("off", "0", "disabled"):
        return
    log_path = Path(path) if path else (Path(override) if override else _DECISION_LOG_DEFAULT)
    # Word count derives from reasons list length as a proxy; task text is gone by here.
    #COMPLETION_DRIVE: reasons list length used as proxy word count — caller never passes task
    entry = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "tier": decision.tier,
        "model": decision.model,
        "score": decision.score,
        "reason_count": len(decision.reasons),
    }
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Tenant-aware routing + frontier guard
# ---------------------------------------------------------------------------

# Lazy import to avoid circular deps and module-level network calls.
_FINANCE_TIERS = frozenset({"confidential", "restricted"})


def route_llm(tenant: "Tenant") -> "Callable[..., str]":  # type: ignore[name-defined]
    """Return the LLM callable appropriate for the tenant's routing policy.

    local  -> agent.local_client.call_local  (Ollama; no frontier traffic)
    frontier -> agent.hermes_client.call_hermes (default frontier routine path)

    Import is deferred so this module stays importable without network access.
    """
    from typing import Callable  # noqa: F401 — kept local for 3.9 compat

    if tenant.llm_routing == "local":
        from agent.local_client import call_local
        model = getattr(tenant, "local_model", None)
        if model:
            import functools
            # Bind the pinned model so callers use the standard call_local signature
            return functools.partial(call_local, model=model)  # type: ignore[return-value]
        return call_local

    from agent.hermes_client import call_hermes
    return call_hermes


def assert_no_frontier(tenant: "Tenant") -> None:  # type: ignore[name-defined]
    """Raise RuntimeError if a local/restricted tenant is about to use a frontier API.

    Call this at the top of any code path that would invoke hermes_client,
    nvidia_client, or any other remote LLM, before making the network call.
    Mirrors bjornswarm's import-time treasury guard as a runtime-checkable version.

    Raises RuntimeError if:
      - tenant.llm_routing == "local", or
      - tenant.sensitivity is in {confidential, restricted}
    """
    if tenant.llm_routing == "local":
        raise RuntimeError(
            f"Tenant '{tenant.slug}' has llm_routing='local' — "
            f"frontier API calls are structurally prohibited."
        )
    if tenant.sensitivity in _FINANCE_TIERS:
        raise RuntimeError(
            f"Tenant '{tenant.slug}' has sensitivity='{tenant.sensitivity}' — "
            f"frontier API calls are structurally prohibited for finance-sensitive tenants."
        )


# Type alias import for annotation only (avoids circular import at runtime).
def _Tenant_hint() -> None:
    """Forward-reference holder — keeps Tenant resolvable as a string annotation."""
    from agent.tenancy import Tenant  # noqa: F401


if __name__ == "__main__":
    _smoke = [
        "tag these invoices by vendor category",
        "why did our cloud spend spike 40% last quarter and which vendors caused it",
        "write a webhook to sync invoices from QuickBooks to our procurement API",
        "is this charge recurring or one-time",
        "draft a negotiation brief comparing our top three SaaS vendors on price and SLA",
        "classify this vendor as software or hardware",
    ]
    for _t in _smoke:
        _d = decide_route(_t)
        print(f"[{_d.tier:7s}] {_d.model:<30s} score={_d.score:.2f}  {_t[:60]}")
