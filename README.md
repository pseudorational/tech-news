# Technology Brief

Daily technology-industry analyst reports, published at **https://pseudorational.github.io/tech-news/**.

The repository contains public-facing reports and a small GitHub Pages site. The reporting agent researches and validates each edition locally, then commits a sanitized report under `reports/YYYY-MM-DD.md`. GitHub Pages builds from `main` at the repository root. The landing page and archive discover reports automatically; no index update is needed.

## Prepare an edition

```sh
python3 scripts/prepare_publication.py /path/to/technology_report_YYYY-MM-DD.md --output /tmp/publication-packet.json
python3 -m unittest discover -s tests -v
```

The JSON packet contains the destination path, public Markdown, and content hashes. The agent uploads that exact content through the connected GitHub integration, verifies the remote file, and checks the deployed page. This helper performs no network requests and needs no credentials.

Only completed editions can be prepared. The exporter validates dates, removes operational metadata and the manual-test appendix, normalizes source access notes, rejects local paths and credential-like strings, and rejects executable HTML, embedded media, and unsafe link schemes. It does not fact-check the report; source verification must precede publication. Review unfamiliar report formats rather than weakening validation.

## Scheduling and retries

Research starts daily at 9 a.m. America/New_York. Hourly checks continue through 4 p.m. until research and publication succeed. A valid local report is reused when only upload or deployment failed. Identical public content is not committed again. Publication state is kept locally and is never added to this repository.

The schedule runs in the user's reporting environment, not on GitHub. GitHub Pages handles publication after a report commit; it does not access subscriber browser sessions or generate research.

## Sources and limitations

Reports summarize evidence in original language and link to reporting and primary disclosures. They identify data cutoffs, analyst interpretation, and material coverage gaps. This repository does not include copied subscription articles, browser sessions, local logs, or private reporting instructions. AI-assisted analysis is provided for information and discussion.

