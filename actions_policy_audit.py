#!/usr/bin/env python3
"""Offline, dependency-free preflight for GitHub Actions workflow policy."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


WORKFLOW_SUFFIXES = {".yml", ".yaml"}
FULL_SHA = re.compile(r"^[0-9a-fA-F]{40}$")
USES = re.compile(r"^\s*-?\s*uses:\s*['\"]?([^\s'\"]+)")


@dataclass(frozen=True)
class Finding:
    rule: str
    severity: str
    file: str
    line: int
    message: str


def workflow_files(target: Path) -> list[Path]:
    if target.is_file():
        return [target] if target.suffix.lower() in WORKFLOW_SUFFIXES else []
    workflow_dir = target / ".github" / "workflows"
    if not workflow_dir.is_dir():
        return []
    return sorted(path for path in workflow_dir.iterdir() if path.is_file() and path.suffix.lower() in WORKFLOW_SUFFIXES)


def display_path(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return path.name


def audit_file(path: Path, root: Path) -> list[Finding]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    shown = display_path(path, root)
    findings: list[Finding] = []

    permissions_lines = [number for number, line in enumerate(lines, 1) if re.match(r"^\s*permissions\s*:", line)]
    if not permissions_lines:
        findings.append(Finding("explicit-permissions", "high", shown, 1, "Declare least-privilege permissions explicitly."))

    if not any(re.match(r"^\s*timeout-minutes\s*:", line) for line in lines):
        findings.append(Finding("job-timeout", "medium", shown, 1, "Set timeout-minutes to bound runaway jobs and cost."))

    for number, line in enumerate(lines, 1):
        match = USES.match(line)
        if not match:
            continue
        reference = match.group(1)
        if reference.startswith(("./", "docker://")):
            continue
        if "@" not in reference:
            findings.append(Finding("action-reference", "high", shown, number, "External action has no version reference."))
            continue
        revision = reference.rsplit("@", 1)[1]
        if not FULL_SHA.fullmatch(revision):
            findings.append(Finding("immutable-action", "high", shown, number, "Pin external actions to a full commit SHA."))

    if re.search(r"^\s*pull_request_target\s*:", text, re.MULTILINE):
        findings.append(Finding("pull-request-target", "high", shown, 1, "Review pull_request_target carefully; it processes untrusted pull-request context."))

    if "actions/upload-artifact@" in text and not re.search(r"^\s*retention-days\s*:", text, re.MULTILINE):
        findings.append(Finding("artifact-retention", "medium", shown, 1, "Set retention-days for uploaded artifacts to bound storage."))

    return findings


def audit(target: Path) -> dict[str, object]:
    files = workflow_files(target)
    root = target if target.is_dir() else target.parent
    findings = [finding for path in files for finding in audit_file(path, root)]
    counts = {severity: sum(item.severity == severity for item in findings) for severity in ("high", "medium")}
    return {
        "schema_version": 1,
        "tool": "actions-policy-audit",
        "network_used": False,
        "files_scanned": len(files),
        "finding_counts": counts,
        "findings": [asdict(item) for item in findings],
    }


def render_text(result: dict[str, object]) -> str:
    lines = [f"Scanned {result['files_scanned']} workflow file(s)."]
    findings = result["findings"]
    assert isinstance(findings, list)
    for item in findings:
        lines.append(f"{item['severity'].upper():6} {item['file']}:{item['line']} {item['rule']}: {item['message']}")
    counts = result["finding_counts"]
    lines.append(f"Findings: {counts['high']} high, {counts['medium']} medium")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit GitHub Actions workflows without network access or credentials")
    parser.add_argument("target", nargs="?", default=".", help="repository root or workflow file")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--fail-on", choices=("high", "any", "none"), default="high")
    args = parser.parse_args(argv)
    target = Path(args.target)
    if not target.exists():
        parser.error(f"target does not exist: {target}")

    result = audit(target)
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.format == "json" else render_text(result))
    counts = result["finding_counts"]
    if args.fail_on == "high" and counts["high"]:
        return 1
    if args.fail_on == "any" and (counts["high"] or counts["medium"]):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
