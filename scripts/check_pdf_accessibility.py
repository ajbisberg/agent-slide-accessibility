from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path


PAGE_RE = re.compile(r"/pages\[(\d+)\]")


def configure_stdio() -> None:
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run veraPDF PDF/UA checks and summarize an accessibility score plus a "
            "fix checklist for a PDF."
        )
    )
    parser.add_argument("pdf", type=Path, help="Path to the PDF to check.")
    parser.add_argument(
        "--flavour",
        default="ua1",
        choices=["ua1", "ua2"],
        help="veraPDF accessibility profile to use.",
    )
    parser.add_argument(
        "--verapdf",
        type=Path,
        help="Explicit path to verapdf or verapdf.bat. Defaults to PATH, then common local installs.",
    )
    parser.add_argument(
        "--max-examples",
        type=int,
        default=5,
        help="Maximum sample failures to show per checklist item.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path to write the plain-text report. Defaults beside the input PDF.",
    )
    parser.add_argument(
        "--raw-json-output",
        type=Path,
        help="Optional path to save the raw veraPDF JSON payload. Defaults beside the input PDF.",
    )
    return parser.parse_args()


def resolve_verapdf(explicit_path: Path | None) -> Path:
    candidates: list[Path] = []

    if explicit_path is not None:
        candidates.append(explicit_path)

    for name in ("verapdf", "verapdf.bat", "verapdf.exe"):
        found = shutil.which(name)
        if found:
            candidates.append(Path(found))

    candidates.extend(
        [
            Path(r"Z:\dev\verapdf\verapdf.bat"),
            Path(r"C:\verapdf\verapdf.bat"),
            Path(r"C:\Program Files\verapdf\verapdf.bat"),
        ]
    )

    for candidate in candidates:
        if candidate.exists():
            return candidate

    raise FileNotFoundError(
        "Could not find veraPDF. Pass --verapdf or ensure 'verapdf' is on PATH."
    )


def build_command(verapdf_path: Path, pdf_path: Path, flavour: str) -> list[str]:
    base_cmd = [
        str(verapdf_path),
        "--format",
        "json",
        "--flavour",
        flavour,
        "--maxfailuresdisplayed",
        "5",
        str(pdf_path),
    ]
    if verapdf_path.suffix.lower() in {".bat", ".cmd"}:
        return ["cmd", "/c", *base_cmd]
    return base_cmd


def run_verapdf(verapdf_path: Path, pdf_path: Path, flavour: str) -> tuple[int, str, str]:
    command = build_command(verapdf_path, pdf_path, flavour)
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return completed.returncode, completed.stdout, completed.stderr


def extract_report_payload(stdout: str) -> dict:
    try:
        return json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("veraPDF did not return valid JSON output.") from exc


def extract_pages(checks: list[dict]) -> list[int]:
    pages: set[int] = set()
    for check in checks:
        context = str(check.get("context", ""))
        for match in PAGE_RE.finditer(context):
            pages.add(int(match.group(1)) + 1)
    return sorted(pages)


def unique_messages(checks: list[dict], limit: int) -> list[str]:
    messages: list[str] = []
    seen: set[str] = set()
    for check in checks:
        message = str(check.get("errorMessage", "")).strip()
        if message and message not in seen:
            seen.add(message)
            messages.append(message)
        if len(messages) >= limit:
            break
    return messages


def fix_hint(rule_summary: dict) -> str:
    description = str(rule_summary.get("description", ""))
    tags = {str(tag).lower() for tag in rule_summary.get("tags", [])}
    obj = str(rule_summary.get("object", ""))

    if "metadata stream" in description.lower() or "metadata" in tags:
        return (
            "Add document-level XMP metadata so the catalog has a /Metadata stream "
            "with /Type /Metadata and /Subtype /XML."
        )
    if obj == "PDLinkAnnot" or ("annotation" in tags and "alt-text" in tags):
        return (
            "Give every visible link annotation a human-readable description in its "
            "Contents entry, or provide equivalent Alt text on the enclosing structure element."
        )
    if "artifact" in tags:
        return (
            "Mark decorative or repeated page content as /Artifact. If the content is meaningful, "
            "place it inside the tagged structure tree instead."
        )
    if "heading" in tags:
        return (
            "Normalize heading order so the first heading is H1 and later headings do not skip "
            "levels when descending."
        )
    if obj == "SEFigure" or "figure" in tags:
        return (
            "Add Alt or ActualText to each meaningful figure. If an image is purely decorative, "
            "mark it as an artifact instead of a figure."
        )
    if "list" in tags:
        return (
            "Restructure lists to use L > LI > Lbl and LBody. Do not place nested list elements "
            "directly inside LI without the required wrappers."
        )
    if "non-standard structure type" in description.lower() or "structure" in tags:
        return (
            "Replace custom structure tags with standard PDF tags, or add a RoleMap that maps "
            "custom tags like Strong or Em to standard equivalents."
        )
    return "Review the failed clause and update the PDF tags or metadata to satisfy that PDF/UA rule."


def score_label(score: float) -> str:
    if score >= 95:
        return "strong"
    if score >= 85:
        return "usable but needs cleanup"
    if score >= 70:
        return "weak"
    return "poor"


def default_output_paths(pdf_path: Path) -> tuple[Path, Path]:
    report_path = pdf_path.with_name(f"{pdf_path.stem}.accessibility.txt")
    raw_json_path = pdf_path.with_name(f"{pdf_path.stem}.verapdf.json")
    return report_path, raw_json_path


def format_report(pdf_path: Path, flavour: str, payload: dict, max_examples: int) -> str:
    jobs = payload.get("report", {}).get("jobs", [])
    if not jobs:
        raise RuntimeError("veraPDF JSON did not include any jobs.")

    validation_result = jobs[0].get("validationResult", [])
    if not validation_result:
        raise RuntimeError("veraPDF JSON did not include a validation result.")

    result = validation_result[0]
    details = result.get("details", {})
    rule_summaries = details.get("ruleSummaries", [])

    passed_rules = int(details.get("passedRules", 0))
    failed_rules = int(details.get("failedRules", 0))
    passed_checks = int(details.get("passedChecks", 0))
    failed_checks = int(details.get("failedChecks", 0))
    total_rules = max(passed_rules + failed_rules, 1)
    total_checks = max(passed_checks + failed_checks, 1)

    rule_score = 100.0 * passed_rules / total_rules
    check_score = 100.0 * passed_checks / total_checks

    lines: list[str] = []
    lines.append(f"Accessibility report for: {pdf_path}")
    lines.append(f"veraPDF profile: PDF/{flavour.upper()}")
    lines.append(f"Compliance result: {'PASS ✓' if result.get('compliant') else 'FAIL ✗'}")
    lines.append(
        f"Accessibility score: {rule_score:.1f}/100 ({passed_rules}/{total_rules} rules passed, {score_label(rule_score)})"
    )
    lines.append(
        f"Check coverage: {check_score:.1f}% ({passed_checks}/{total_checks} individual checks passed)"
    )
    lines.append("")

    if not rule_summaries:
        lines.append("No failing rules were reported.")
        return "\n".join(lines)

    lines.append("Checklist")
    sorted_rules = sorted(
        rule_summaries,
        key=lambda item: int(item.get("failedChecks", 0)),
        reverse=True,
    )

    for index, rule in enumerate(sorted_rules, start=1):
        checks = rule.get("checks", [])
        pages = extract_pages(checks)
        messages = unique_messages(checks, max_examples)
        tags = ", ".join(str(tag) for tag in rule.get("tags", [])) or "none"
        clause = f"{rule.get('specification', 'Unknown spec')} clause {rule.get('clause', '?')}"
        failed = int(rule.get("failedChecks", 0))

        lines.append(
            f"{index}. ☐ {clause} [{failed} failed checks | tags: {tags}]"
        )
        lines.append(f"   Issue: {rule.get('description', '').strip()}")
        lines.append(f"   Fix: {fix_hint(rule)}")
        if pages:
            page_text = ", ".join(str(page) for page in pages[:12])
            if len(pages) > 12:
                page_text += ", …"
            lines.append(f"   Pages: {page_text}")
        for message in messages:
            lines.append(f"   Example: {message}")
        if len(checks) > len(messages):
            lines.append(
                f"   Note: veraPDF reported {len(checks)} example instances for this rule in the JSON output."
            )
        lines.append("")

    lines.append("Scoring note: the score above is a heuristic based on PDF/UA rule pass rate, not an official veraPDF metric.")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    configure_stdio()
    args = parse_args()
    pdf_path = args.pdf.resolve()
    if not pdf_path.exists():
        print(f"PDF not found: {pdf_path}", file=sys.stderr)
        return 2

    try:
        verapdf_path = resolve_verapdf(args.verapdf.resolve() if args.verapdf else None)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    default_report_path, default_raw_json_path = default_output_paths(pdf_path)
    report_output_path = args.output.resolve() if args.output else default_report_path
    raw_json_output_path = (
        args.raw_json_output.resolve() if args.raw_json_output else default_raw_json_path
    )

    exit_code, stdout, stderr = run_verapdf(verapdf_path, pdf_path, args.flavour)
    raw_json_output_path.parent.mkdir(parents=True, exist_ok=True)
    raw_json_output_path.write_text(stdout, encoding="utf-8")

    if not stdout.strip():
        if stderr.strip():
            print(stderr.strip(), file=sys.stderr)
        else:
            print("veraPDF produced no output.", file=sys.stderr)
        return exit_code or 1

    try:
        payload = extract_report_payload(stdout)
        report = format_report(pdf_path, args.flavour, payload, args.max_examples)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        if stderr.strip():
            print(stderr.strip(), file=sys.stderr)
        return exit_code or 1

    report_output_path.parent.mkdir(parents=True, exist_ok=True)
    report_output_path.write_text(report, encoding="utf-8")

    sys.stdout.write(report)
    if stderr.strip():
        sys.stderr.write(stderr)

    return 0 if exit_code in (0, 1) else exit_code


if __name__ == "__main__":
    raise SystemExit(main())
