from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from prepare_publication import prepare


def report(status="complete", extra=""):
    sections = "\n\n".join(f"## {i}. Section {i}\n\nEvidence [A](https://example.com/a), [B](https://example.com/b), [C](https://example.com/c)." for i in range(1, 12))
    return f'''---
report_date: 2026-10-22
status: {status}
news_cutoff: "2026-10-22T09:00:00-04:00"
market_session: 2026-10-21
completed_at: "2026-10-22T09:20:00-04:00"
---
# Local report
Private preamble in /Users/example/private.

{sections}
{extra}
'''


class PublicationTests(unittest.TestCase):
    def prepare_text(self, text, name="technology_report_2026-10-22.md"):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / name
            path.write_text(text)
            return prepare(path)

    def test_public_metadata_and_private_appendix(self):
        text = report(extra="\n### Coverage gaps and manual-test findings\n\nPrivate /Users/example/path")
        result = self.prepare_text(text)
        self.assertNotIn("/Users/", result["content"])
        self.assertNotIn("completed_at", result["content"])
        self.assertIn('permalink: "/reports/2026-10-22/"', result["content"])
        self.assertEqual(result["path"], "reports/2026-10-22.md")
        self.assertEqual(result, self.prepare_text(text))

    def test_rejects_partial_and_date_mismatch(self):
        for text, name in [(report("failed"), "technology_report_2026-10-22.md"), (report(), "technology_report_2026-10-23.md"), (report(), "technology_report_2026-10-22.partial.md")]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.prepare_text(text, name)

    def test_rejects_sensitive_or_executable_content(self):
        for extra in ["/Users/person/private", "<script>alert(1)</script>", "[click](javascript:alert)", "{{ site.secret }}", "api_key=secret", "![article](https://example.com/a.png)"]:
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                self.prepare_text(report(extra=extra))

    def test_rejects_missing_sections_or_timezone(self):
        for text in [report().replace("## 6. Section 6", "## 60. Section 6"), report().replace("2026-10-22T09:00:00-04:00", "2026-10-22T09:00:00")]:
            with self.assertRaises(ValueError):
                self.prepare_text(text)

    def test_financial_tables_remain_intact(self):
        table = "| [Company](https://example.com/company) | 10 | 20 | 30 | 40 |"
        result = self.prepare_text(report(extra=table))
        self.assertIn(table, result["content"])
        self.assertEqual(len(result["edition_digest"]), 64)
        changed = self.prepare_text(report(extra=table + "\nRevised analyst interpretation."))
        self.assertNotEqual(result["edition_digest"], changed["edition_digest"])


if __name__ == "__main__":
    unittest.main()
