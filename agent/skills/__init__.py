"""
__init__.py — Import skill modules so registration fires on `import agent.skills`.

Exposes the registry API for callers: register, get, all_skills, all_skills_names,
run_skill, to_nat_function.
"""

from agent.skills.base import (  # noqa: F401
    Skill,
    all_skills,
    all_skills_names,
    get,
    register,
    run_skill,
    to_nat_function,
)

# Import order determines registration order; keep alphabetical for determinism.
import agent.skills.access_governance_skill  # noqa: F401
import agent.skills.anomaly_detect_skill     # noqa: F401
import agent.skills.approval_gate_skill      # noqa: F401
import agent.skills.audit_skill              # noqa: F401
import agent.skills.handle_402_skill         # noqa: F401
import agent.skills.invoice_ingest_skill     # noqa: F401
import agent.skills.onboarding_skill         # noqa: F401
import agent.skills.pay_invoice_skill        # noqa: F401
import agent.skills.vendor_analyze_skill     # noqa: F401
