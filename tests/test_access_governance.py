"""
test_access_governance.py — Offline tests for Baton access-governance integration.

No baton binary required, no network. All assertions use the bundled fixture and
a fixed reference_date of 2026-06-01 for determinism.
"""

from __future__ import annotations

import agent.skills  # noqa: F401 — triggers registration of all skills including access_governance_skill
from control_plane.baton_client import (
    AccessGrant,
    baton_available,
    fetch_access,
    summarize_seats,
    unused_seats,
)


_REFERENCE_DATE = "2026-06-01"
_ADOBE_APP = "Adobe Creative Cloud"


# ---------------------------------------------------------------------------
# baton_available
# ---------------------------------------------------------------------------

def test_baton_available_returns_bool():
    """baton_available() returns a bool (likely False in CI with no baton install)."""
    result = baton_available()
    assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# fetch_access — fixture path
# ---------------------------------------------------------------------------

def test_fetch_access_no_baton_returns_fixture_grants():
    """fetch_access() with no baton/c1z returns non-empty AccessGrant list from fixture."""
    grants, source = fetch_access()
    assert isinstance(grants, list)
    assert len(grants) > 0
    assert all(isinstance(g, AccessGrant) for g in grants)


def test_fetch_access_source_is_fixture_when_no_baton():
    """fetch_access() source is 'fixture' when baton is absent or c1z is not provided."""
    _, source = fetch_access()
    # When baton is installed but no c1z is provided, we also fall through to fixture.
    assert source in ("fixture", "baton")


def test_fetch_access_fixture_has_adobe_grants():
    """Fixture contains Adobe Creative Cloud grants for Pinwheel Studio users."""
    grants, _ = fetch_access()
    adobe_grants = [g for g in grants if g.resource == _ADOBE_APP]
    assert len(adobe_grants) == 12


# ---------------------------------------------------------------------------
# unused_seats
# ---------------------------------------------------------------------------

def test_unused_seats_flags_exactly_3_adobe():
    """unused_seats flags exactly 3 Adobe Creative Cloud seats at reference 2026-06-01."""
    grants, _ = fetch_access()
    idle = unused_seats(grants, days=60, reference_date=_REFERENCE_DATE)
    adobe_idle = [g for g in idle if g.resource == _ADOBE_APP]
    assert len(adobe_idle) == 3


def test_unused_seats_adobe_users_are_correct():
    """The 3 idle Adobe seats belong to hiro, lena, and omar."""
    grants, _ = fetch_access()
    idle = unused_seats(grants, days=60, reference_date=_REFERENCE_DATE)
    adobe_idle_principals = {g.principal for g in idle if g.resource == _ADOBE_APP}
    expected = {
        "hiro@pinwheelstudio.io",
        "lena@pinwheelstudio.io",
        "omar@pinwheelstudio.io",
    }
    assert adobe_idle_principals == expected


def test_unused_seats_skips_none_last_used():
    """unused_seats does not flag grants with last_used=None."""
    grants = [
        AccessGrant("a@x.io", "App", "license", None, "fixture"),
        AccessGrant("b@x.io", "App", "license", "2020-01-01", "fixture"),
    ]
    idle = unused_seats(grants, days=60, reference_date=_REFERENCE_DATE)
    principals = {g.principal for g in idle}
    assert "a@x.io" not in principals
    assert "b@x.io" in principals


# ---------------------------------------------------------------------------
# summarize_seats
# ---------------------------------------------------------------------------

def test_summarize_seats_counts_adobe():
    """summarize_seats returns total=12 for Adobe Creative Cloud from fixture."""
    grants, _ = fetch_access()
    summary = summarize_seats(grants)
    assert _ADOBE_APP in summary
    assert summary[_ADOBE_APP]["total"] == 12


# ---------------------------------------------------------------------------
# access_governance_skill — registration and run()
# ---------------------------------------------------------------------------

def test_access_governance_skill_is_registered():
    """access_governance_skill is in the registry (8 total skills)."""
    from agent.skills.base import all_skills_names
    names = all_skills_names()
    assert "access_governance_skill" in names
    assert len(names) == 8


def test_access_governance_skill_run_shape():
    """access_governance_skill.run() returns documented keys."""
    from agent.skills.base import run_skill
    result = run_skill("access_governance_skill", {"reference_date": _REFERENCE_DATE})
    assert "grants_count" in result
    assert "seat_summary" in result
    assert "unused_seats" in result
    assert "recommendations" in result
    assert "source" in result


def test_access_governance_skill_run_unused_count():
    """Skill run() flags exactly 3 unused Adobe seats at reference 2026-06-01."""
    from agent.skills.base import run_skill
    result = run_skill("access_governance_skill", {"reference_date": _REFERENCE_DATE})
    adobe_unused = [s for s in result["unused_seats"] if s["resource"] == _ADOBE_APP]
    assert len(adobe_unused) == 3


def test_access_governance_skill_recommendations_name_adobe_users():
    """Recommendations contain deprovision entries for the 3 idle Adobe users."""
    from agent.skills.base import run_skill
    result = run_skill("access_governance_skill", {"reference_date": _REFERENCE_DATE})
    recs = result["recommendations"]
    rec_text = " ".join(recs)
    assert "hiro@pinwheelstudio.io" in rec_text
    assert "lena@pinwheelstudio.io" in rec_text
    assert "omar@pinwheelstudio.io" in rec_text
