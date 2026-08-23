"""Private, offline report generation."""

from cutsignal.reporting.html import render_html_report
from cutsignal.reporting.profiles import ReportProfile, build_report_payload

__all__ = ["ReportProfile", "build_report_payload", "render_html_report"]
