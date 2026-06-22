"""config/model_routing.py: Task-to-model routing table for the STR agent.

Nemotron Ultra handles reasoning-heavy tasks (anomaly detection, dynamic pricing,
AEO scoring). Hermes-small (Nemotron Super) handles lightweight formatting,
classification, and template rendering. No Chinese-origin models are present or
permitted.

Model IDs are read from environment variables so they stay consistent with the
actual client callers (nvidia_client.py uses NEMOTRON_MODEL; hermes_client.py
uses HERMES_MODEL). Constants here mirror those defaults exactly.

Public API:
    MODEL_ROUTING: dict mapping task name -> model identifier string
    route_for(task): return model identifier for a task; raises KeyError on unknown task
    NEMOTRON_ULTRA: canonical Nemotron Ultra model identifier constant
    HERMES_SMALL: canonical Hermes-small (Nemotron Super) model identifier constant
"""
from __future__ import annotations

import os

# Model identifier constants: match the defaults in nvidia_client.py and
# hermes_client.py so routing table, clients, and env vars stay in sync.
# Override via NEMOTRON_MODEL / HERMES_MODEL in the environment.
NEMOTRON_ULTRA: str = os.environ.get(
    "NEMOTRON_MODEL", "nvidia/nemotron-3-ultra-550b-a55b"
)
HERMES_SMALL: str = os.environ.get(
    "HERMES_MODEL", "nvidia/nemotron-3-super-120b-a12b"
)
# Nous Research Hermes model (hermes_client.py endpoint, separate from NVIDIA Nemotron-Super)
HERMES_NOUS: str = os.environ.get(
    "HERMES_MODEL", "nousresearch/hermes-4-70b"
)

# Tasks that demand multi-step reasoning or pricing optimization go to Nemotron Ultra.
# Tasks that are classification, formatting, or templating go to Hermes-small.
MODEL_ROUTING: dict[str, str] = {
    # Nemotron Ultra tier: anomaly detection, pricing, AEO reasoning
    "anomaly_detection": NEMOTRON_ULTRA,
    "dynamic_pricing": NEMOTRON_ULTRA,
    "aeo_scoring": NEMOTRON_ULTRA,
    "aeo_reasoning": NEMOTRON_ULTRA,
    "revenue_analysis": NEMOTRON_ULTRA,
    "management_fee_audit": NEMOTRON_ULTRA,
    # Hermes-small tier: classification, formatting, template rendering
    "listing_format": HERMES_SMALL,
    "guest_message_classify": HERMES_SMALL,
    "crew_dispatch_template": HERMES_SMALL,
    "booking_confirmation_template": HERMES_SMALL,
    "owner_report_template": HERMES_SMALL,
    "expense_categorize": HERMES_SMALL,
    # Nous Research Hermes tier: guest comms intent triage + sales reply drafting
    "guest_comms": HERMES_NOUS,
}

_BANNED_ORIGIN_SUBSTRINGS: tuple[str, ...] = (
    "qwen", "deepseek", "yi-", "baichuan", "glm", "chatglm",
    "internlm", "minimax", "moonshot", "kimi", "hunyuan",
)


def _assert_no_chinese_models() -> None:
    """Raise AssertionError if any routing value contains a banned model substring."""
    for task, model in MODEL_ROUTING.items():
        lower = model.lower()
        for banned in _BANNED_ORIGIN_SUBSTRINGS:
            assert banned not in lower, (
                f"Chinese-origin model banned by policy: task={task!r} model={model!r} "
                f"matched banned substring {banned!r}"
            )


_assert_no_chinese_models()


def route_for(task: str) -> str:
    """Return the model identifier for the given task name.

    Raises KeyError when task is not in MODEL_ROUTING.
    """
    if task not in MODEL_ROUTING:
        raise KeyError(
            f"Unknown STR task {task!r}. Known tasks: {sorted(MODEL_ROUTING)}"
        )
    return MODEL_ROUTING[task]
