#!/usr/bin/env python3
"""Prepare a completed local edition for public GitHub Pages publication."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date, datetime
from pathlib import Path
import re
from urllib.parse import urlsplit

REPOSITORY = "pseudorational/tech-news"
SITE = "https://pseudorational.github.io/tech-news"
VALID_STATUSES = {"complete", "complete_with_gaps"}
SECTION_IDS = tuple(range(1, 12))


def flat_front_matter(text: str) -> tuple[dict[str, str], str]:
    """Read the report's flat metadata without evaluating arbitrary YAML tags."""
    text = text.replace("\r\n", "\n")
    if not text.startswith("---\n"):
        raise ValueError("Report must begin with YAML front matter")
    marker = text.find("\n---\n", 4)
    if marker < 0:
        raise ValueError("Missing front-matter terminator")
    metadata: dict[str, str] = {}
    for line in text[4:marker].splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = re.fullmatch(r"([a-z][a-z0-9_]*):\s*(.*)", line)
        if not match:
            raise ValueError("Report metadata must use a flat key/value format")
        key, value = match.groups()
        if key in metadata:
            raise ValueError(f"Duplicate metadata key: {key}")
        if value.startswith('"'):
            value = json.loads(value)
        elif value.startswith("'") and value.endswith("'"):
            value = value[1:-1].replace("''", "'")
        if not isinstance(value, str):
            raise ValueError(f"Metadata {key} must be a scalar")
        metadata[key] = value
    return metadata, text[marker + 5 :].lstrip()


def checked_date(value: str, label: str) -> str:
    try:
        parsed = date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid {label}") from exc
    if parsed.isoformat() != value:
        raise ValueError(f"{label} must use YYYY-MM-DD")
    return value


def checked_timestamp(value: str, label: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise ValueError(f"Invalid {label}") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{label} requires a timezone offset")
    return value


def normalize_source_row(line: str) -> str:
    if not line.startswith("| ["):
        return line
    columns = [part.strip() for part in line.strip().strip("|").split("|")]
    if len(columns) != 4:
        raise ValueError("Source register must have four columns")
    access = columns[3].lower()
    if "full article" in access or "full subscriber" in access or "full text" in access or "full recap" in access:
        columns[3] = "Full text reviewed."
    elif "excerpt" in access or "headline" in access or "snippet" in access:
        columns[3] = "Headline or excerpt only."
    elif "primary" in access:
        columns[3] = "Primary disclosure reviewed."
    else:
        columns[3] = "Source reviewed; limitations described in the report."
    return "| " + " | ".join(columns) + " |"


def validate_public_text(text: str) -> None:
    if re.search(r"/(?:Users|users|home|private|var/folders)/", text):
        raise ValueError("Public report contains a local filesystem path")
    if re.search(r"(?i)\b(?:authorization\s*:\s*bearer|api[_ -]?key\s*[:=]|github_token\s*[:=])", text):
        raise ValueError("Public report contains credential-like text")
    if re.search(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9]{24,})", text):
        raise ValueError("Public report contains a credential-like value")
    if re.search(r"</?[A-Za-z][^>]*>", text) or "![" in text:
        raise ValueError("Raw HTML and embedded media are not permitted in report Markdown")
    if re.search(r"(?i)(?:javascript|data|file|vbscript)\s*:", text):
        raise ValueError("Unsafe URI scheme in report")
    if re.search(r"\{[%{]", text):
        raise ValueError("Liquid template syntax is not permitted in reports")
    for url in re.findall(r"\]\(([^)\s]+)\)", text):
        parsed = urlsplit(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("Report links must be credential-free HTTP(S) URLs")
        if parsed.hostname.lower() in {"localhost", "127.0.0.1", "::1"}:
            raise ValueError("Local links are not suitable for publication")
    if re.search(r"(?i)(?:subscriber Chrome|Work browser|native Chrome|browser connection|computer-use session|sandbox|configured writable|automation_readiness|CORE_REPORTING_PROMPT)", text):
        raise ValueError("Operational setup details remain in public report")


def prepare(source: Path) -> dict[str, str]:
    match = re.fullmatch(r"technology_report_(\d{4}-\d{2}-\d{2})\.md", source.name)
    if not match:
        raise ValueError("Only a final daily report filename can be published")
    original = source.read_text(encoding="utf-8")
    metadata, body = flat_front_matter(original)
    report_date = checked_date(metadata.get("report_date", ""), "report date")
    if match.group(1) != report_date:
        raise ValueError("Filename and report date do not match")
    status = metadata.get("status", "")
    if status not in VALID_STATUSES:
        raise ValueError("An incomplete report cannot be published")
    cutoff = checked_timestamp(metadata.get("news_cutoff", ""), "news cutoff")
    session = checked_date(metadata.get("market_session", ""), "market session")
    checked_timestamp(metadata.get("completed_at", ""), "completion time")
    start = re.search(r"(?m)^## 1\. ", body)
    if start is None:
        raise ValueError("Executive section missing")
    # The local preamble is operational; the public template supplies report metadata.
    body = body[start.start():]
    cutoff_section = re.search(r"(?m)^### Coverage gaps and manual-test findings\s*$", body)
    if cutoff_section:
        body = body[:cutoff_section.start()].rstrip()
    body = body.replace("Full WSJ reporting, now verified in the authenticated Work browser connection,", "WSJ reporting")
    body = body.replace("A full-text Economist article reviewed in the signed-in Work window", "An Economist article")
    lines = []
    in_sources = False
    for line in body.splitlines():
        if line.strip() == "### Source register":
            in_sources = True
        elif line.startswith("##"):
            in_sources = False
        lines.append(normalize_source_row(line) if in_sources else line)
    body = "\n".join(lines)
    body = body.replace("Retrieval windows below are actual manual-test batch windows", "Retrieval windows below record when sources were reviewed")
    # Preserve editorial limitations while excluding the local test/debug appendix.
    limitations = []
    if re.search(r"(?i)(?:\*\*NYT:\*\*|New York Times).*?(?:blocked|prohibit|denied|not.*reviewed)", original):
        limitations.append("New York Times coverage was unavailable for this edition.")
    if "No verified volume dashboard" in original:
        limitations.append("Volume, consumer-device demand, a comprehensive calendar, and comparable valuation inputs were not independently verified.")
    if limitations:
        body += "\n\n### Coverage limitations\n\n" + "\n".join("- " + item for item in limitations)
    sections = tuple(int(x) for x in re.findall(r"(?m)^## (\d+)\. ", body))
    if sections != SECTION_IDS:
        raise ValueError("Expected report sections 1 through 11, in order")
    if len(set(re.findall(r"https?://[^)\s]+", body))) < 3:
        raise ValueError("Report needs at least three linked sources")
    validate_public_text(body)
    front = {
        "layout": "report",
        "title": "Technology Industry Analyst Report",
        "report_date": report_date,
        "news_cutoff": cutoff,
        "market_session": session,
        "status": status,
        "permalink": f"/reports/{report_date}/",
    }
    if metadata.get("access_retested_at"):
        front["source_rechecked_at"] = checked_timestamp(metadata["access_retested_at"], "source recheck time")
    if metadata.get("run_type") == "subscriber_connection_retest":
        front["edition_note"] = "Initial late-evening test edition. Selected sources were rechecked after the original news cutoff; market data was not refreshed."
    edition_digest = hashlib.sha256((json.dumps(front, sort_keys=True) + "\n" + body).encode()).hexdigest()
    front["edition_digest"] = edition_digest
    public = "---\nis_report: true\n" + "\n".join(f"{key}: {json.dumps(value, ensure_ascii=False)}" for key, value in front.items()) + "\n---\n\n" + body.rstrip() + "\n"
    return {
        "repository": REPOSITORY,
        "branch": "main",
        "report_date": report_date,
        "path": f"reports/{report_date}.md",
        "content": public,
        "source_sha256": hashlib.sha256(original.encode()).hexdigest(),
        "public_sha256": hashlib.sha256(public.encode()).hexdigest(),
        "edition_digest": edition_digest,
        "published_url": f"{SITE}/reports/{report_date}/",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        packet = prepare(args.report)
    except (ValueError, OSError) as exc:
        parser.exit(2, f"Publication validation failed: {exc}\n")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(packet, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Prepared {packet['path']} ({packet['public_sha256'][:12]}); no upload performed")


if __name__ == "__main__":
    main()

