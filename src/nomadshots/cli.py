"""NomadShots CLI — privacy-first photo metadata audit tool."""
from pathlib import Path

import typer

from .audit import audit_folder
from .exiftool_adapter import ExiftoolError, check_exiftool_available
from .models import format_headline
from .report import generate_report

app = typer.Typer(
    name="nomadshots",
    help="Privacy-first photo metadata tool.",
    no_args_is_help=True,
)


@app.callback()
def main() -> None:
    """Privacy-first photo metadata tool."""
    pass


@app.command("audit")
def audit(
    folder: Path = typer.Argument(..., help="Folder to audit for photo metadata."),
    recursive: bool = typer.Option(False, "--recursive", "-r", help="Scan subdirectories."),
    out: Path = typer.Option(
        Path("./audit-report.md"), "--out", help="Output path for the audit report."
    ),
) -> None:
    """Scan a folder and report sensitive metadata in photos."""
    # Check exiftool is available
    try:
        check_exiftool_available()
    except ExiftoolError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1)

    # Validate folder
    folder = folder.resolve()
    if not folder.exists():
        typer.echo(f"Error: folder does not exist: {folder}", err=True)
        raise typer.Exit(code=1)
    if not folder.is_dir():
        typer.echo(f"Error: not a directory: {folder}", err=True)
        raise typer.Exit(code=1)

    out = out.resolve()
    if out.is_relative_to(folder):
        typer.echo(
            f"Error: report output must be outside the audited folder: {out}",
            err=True,
        )
        raise typer.Exit(code=1)

    # Run audit
    summary = audit_folder(folder, recursive=recursive)

    # Generate report
    generate_report(summary, out)

    # Print terminal summary
    typer.echo(f"\n{format_headline(summary)}")
    typer.echo(f"Files with device info: {summary.files_with_device_info}")
    if summary.file_errors > 0:
        typer.echo(f"Files with errors: {summary.file_errors}")
    typer.echo(f"\nReport written to: {out}")

    # Exit code: 0 = clean, 2 = completed with file errors
    if summary.file_errors > 0:
        raise typer.Exit(code=2)
