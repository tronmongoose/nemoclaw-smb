"""Invoice read routes for nemoclaw-smb dashboard.

Exports (via router):
    GET /invoices                — paginated invoice list, date-desc
    GET /invoices/anomalies      — anomaly scan over seed invoices at given z-threshold
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from fixtures.seed_data import seed_invoices
from gbrain.anomaly_detector import scan

router = APIRouter(prefix="/invoices", tags=["invoices"])

# Module-level cache; seed_invoices() is pure/deterministic so one load is fine.
#GLOBAL-STATE: cached seed invoice list; avoids rebuilding on every request
_INVOICES: list[dict] = sorted(seed_invoices(), key=lambda x: x["date"], reverse=True)


@router.get("")
def list_invoices(limit: int = Query(default=50, ge=1, le=500)) -> list[dict]:
    """Return up to `limit` invoices sorted by date descending.

    Each entry: {invoice_id, vendor, description, amount, date, category}.
    """
    return _INVOICES[:limit]


@router.get("/anomalies")
def list_anomalies(threshold: float = Query(default=2.0, gt=0)) -> list[dict]:
    """Scan seed invoices for vendor spend anomalies at `threshold` z-score.

    Returns dicts with fields:
        vendor, current_amount, baseline_mean, z_score, pct_change, is_anomaly, reason

    Field names match the Anomaly dataclass exactly (no remapping needed).
    """
    anomalies = scan(seed_invoices(), z_threshold=threshold)
    return [
        {
            "vendor": a.vendor,
            "current_amount": a.current_amount,
            "baseline_mean": a.baseline_mean,
            "z_score": a.z_score,
            "pct_change": a.pct_change,
            "is_anomaly": a.is_anomaly,
            "reason": a.reason,
        }
        for a in anomalies
    ]
