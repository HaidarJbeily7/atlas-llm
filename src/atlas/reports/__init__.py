"""Report generation and formatting."""

REPORTER_REGISTRY = {
    "json": "atlas.reports.json_reporter.JSONReporter",
    "html": "atlas.reports.html_reporter.HTMLReporter",
    "markdown": "atlas.reports.markdown_reporter.MarkdownReporter",
    "sarif": "atlas.reports.sarif_reporter.SARIFReporter",
    "junit": "atlas.reports.junit_reporter.JUnitReporter",
}
