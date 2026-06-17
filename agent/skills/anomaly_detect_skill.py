"""
anomaly_detect_skill.py — Scan invoices for spend anomalies; optionally attach Nemotron reasoning.

Exports: skill (registered on import)
"""

from __future__ import annotations

from dataclasses import asdict

from gbrain.anomaly_detector import scan

from agent.skills.base import Skill, register

_INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "invoices": {
            "type": "array",
            "description": "Invoice dicts with keys: vendor, amount, date.",
        },
        "with_reasoning": {
            "type": "boolean",
            "description": "If true, attach Nemotron reasoning for each anomaly (requires API key).",
            "default": False,
        },
        "z_threshold": {
            "type": "number",
            "description": "Z-score threshold for anomaly detection (default 2.0).",
            "default": 2.0,
        },
    },
    "required": ["invoices"],
}


def _run(args: dict) -> dict:
    """Run anomaly detection; attach reasoning when with_reasoning=True."""
    invoices: list[dict] = args["invoices"]
    z_threshold: float = float(args.get("z_threshold", 2.0))
    with_reasoning: bool = bool(args.get("with_reasoning", False))

    anomalies = scan(invoices, z_threshold=z_threshold)
    results = []
    for anomaly in anomalies:
        entry = asdict(anomaly)
        if with_reasoning:
            from agent.reasoning import reason_about_anomaly  # noqa: PLC0415
            entry["reasoning"] = reason_about_anomaly(anomaly, {})
        results.append(entry)

    return {
        "anomaly_count": len(results),
        "anomalies": results,
    }


skill = register(Skill(
    name="anomaly_detect_skill",
    description="Scan invoices for per-vendor spend anomalies using z-score analysis.",
    input_schema=_INPUT_SCHEMA,
    run=_run,
))
