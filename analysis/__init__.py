"""analysis — P&L computation, advisory findings, and report generation.

Exports: compute_pnl, find, build_report, Finding
"""

from analysis.pnl import compute_pnl
from analysis.findings import find, Finding
from analysis.report import build_report

__all__ = ["compute_pnl", "find", "build_report", "Finding"]
