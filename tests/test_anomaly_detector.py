"""Tests for gbrain/anomaly_detector.py.

Covers: score_invoice edge cases, MIN_PCT_CHANGE floor, and scan() against seed data.
"""

import pytest

from fixtures.seed_data import seed_invoices
from gbrain.anomaly_detector import MIN_PCT_CHANGE, Anomaly, scan, score_invoice


# ---------------------------------------------------------------------------
# score_invoice: Adobe history [277,280,275,278] + spike 340 -> anomaly
# ---------------------------------------------------------------------------

ADOBE_HISTORY = [277.0, 280.0, 275.0, 278.0]


def test_adobe_spike_is_anomaly():
    result = score_invoice("Adobe", 340.0, ADOBE_HISTORY)
    assert result.is_anomaly is True
    assert result.vendor == "Adobe"
    assert result.current_amount == 340.0


def test_adobe_spike_pct_change_in_range():
    result = score_invoice("Adobe", 340.0, ADOBE_HISTORY)
    # Mean of [277,280,275,278] = 277.5; (340-277.5)/277.5 * 100 ~ 22.5%
    assert 22.0 <= result.pct_change <= 24.0


def test_adobe_spike_reason_contains_direction():
    result = score_invoice("Adobe", 340.0, ADOBE_HISTORY)
    assert "up" in result.reason.lower()


# ---------------------------------------------------------------------------
# score_invoice: in-range amount -> not anomaly
# ---------------------------------------------------------------------------

def test_normal_invoice_not_anomaly():
    result = score_invoice("Adobe", 279.0, ADOBE_HISTORY)
    assert result.is_anomaly is False


def test_normal_invoice_reason_within_range():
    result = score_invoice("Adobe", 279.0, ADOBE_HISTORY)
    assert "within normal range" in result.reason


# ---------------------------------------------------------------------------
# score_invoice: single-point history -> insufficient history, not anomaly
# ---------------------------------------------------------------------------

def test_single_point_history_not_anomaly():
    result = score_invoice("NewVendor", 500.0, [300.0])
    assert result.is_anomaly is False
    assert "insufficient history" in result.reason


def test_empty_history_not_anomaly():
    result = score_invoice("NewVendor", 500.0, [])
    assert result.is_anomaly is False
    assert "insufficient history" in result.reason
    assert result.baseline_mean == 0.0


# ---------------------------------------------------------------------------
# MIN_PCT_CHANGE floor: a +0.7% move on a tight 3-point sample
# Even if z-score crosses threshold, pct_change < MIN_PCT_CHANGE suppresses it.
# ---------------------------------------------------------------------------

def test_min_pct_change_floor_suppresses_tight_sample():
    # Three identical points: std_dev=0, z=0 -> not anomaly regardless.
    # Use three points very close together so pct_change stays below floor.
    base = [100.0, 100.5, 100.0]
    # +0.7% over mean ~100.17 -> pct_change ~0.7, well below MIN_PCT_CHANGE=8.0
    amount = 100.87  # ~+0.7%
    result = score_invoice("TightVendor", amount, base)
    assert result.is_anomaly is False


def test_min_pct_change_constant_value():
    assert MIN_PCT_CHANGE == 8.0


# ---------------------------------------------------------------------------
# scan(): seed_invoices() returns exactly 1 anomaly (Adobe 340)
# ---------------------------------------------------------------------------

def test_scan_seed_invoices_returns_exactly_one_anomaly():
    invoices = seed_invoices()
    anomalies = scan(invoices)
    assert len(anomalies) == 1


def test_scan_seed_invoices_anomaly_is_adobe():
    invoices = seed_invoices()
    anomalies = scan(invoices)
    assert "Adobe" in anomalies[0].vendor or "adobe" in anomalies[0].vendor.lower()


def test_scan_seed_invoices_anomaly_amount():
    invoices = seed_invoices()
    anomalies = scan(invoices)
    assert anomalies[0].current_amount == 340.0
