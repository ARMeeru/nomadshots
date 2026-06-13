"""Markdown report generator for audit results."""
from pathlib import Path

from .models import AuditSummary, format_headline


def generate_report(summary: AuditSummary, output_path: Path) -> None:
    """Write audit results as a Markdown report.

    Args:
        summary: The audit summary to report.
        output_path: Path to write the markdown file.
    """
    lines: list[str] = []

    lines.append("# NomadShots Audit Report\n")
    lines.append(f"**{format_headline(summary)}**\n")
    lines.append("")
    lines.append("## Summary\n")
    lines.append(f"- Total files scanned: {summary.total_files}")
    lines.append(f"- Files with GPS: {summary.files_with_gps}")
    lines.append(f"- Files with device info: {summary.files_with_device_info}")
    lines.append(f"- Files with errors: {summary.file_errors}")
    lines.append("")
    lines.append("## Per-File Results\n")
    lines.append("| File | GPS | Location | Device | Timestamp | Sensitive Fields | Error |")
    lines.append("|------|-----|----------|--------|-----------|-----------------|-------|")

    for result in summary.results:
        filename = result.filepath.name
        gps = "Yes" if result.has_gps else "No"
        location = result.nearest_location or "—"
        device = f"{result.device_make or ''} {result.device_model or ''}".strip() or "—"
        timestamp = result.capture_time or "—"
        sensitive = ", ".join(result.sensitive_fields) if result.sensitive_fields else "—"
        error = result.error or "—"
        lines.append(f"| {filename} | {gps} | {location} | {device} | {timestamp} | {sensitive} | {error} |")

    lines.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
